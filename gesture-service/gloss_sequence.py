"""
Gloss sequence processing for the Gesture Recognition Service (KAN-18).

Sits between classification and the NLP/LLM layer. It receives the gloss
predicted for every spotted gesture segment and turns the stream of
predictions into a clean, ordered gloss sequence for one utterance
(sentence) of one recognition session.

What it does:
  * keeps predictions in temporal order (by segment start time);
  * binds every sequence to the session it belongs to (session_id);
  * applies confidence rules:
        confidence <  GLOSS_MIN_CONFIDENCE     -> dropped, recorded as a gap
        confidence <  GLOSS_ACCEPT_CONFIDENCE  -> kept, status "uncertain"
        otherwise                              -> kept, status "accepted"
  * merges repeated predictions of the same gloss that are close in time
    (the same sign classified twice, e.g. overlapping segments);
  * records missing predictions (unrecognized segments) as gaps, so the
    NLP layer knows a word may be missing at that position;
  * detects utterance boundaries: a pause with no gesture, an explicit
    finalize, or a maximum utterance length;
  * emits a structured GlossSequence (see docs/websocket-contract.md).

The module does not import the model code, so it can be tested without
torch. A prediction is any object with `.gloss` (list of str) and
`.confidence` (float), or None when classification found nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from constants import (
    GLOSS_ACCEPT_CONFIDENCE,
    GLOSS_MAX_SEQUENCE_LENGTH,
    GLOSS_MIN_CONFIDENCE,
    GLOSS_REPEAT_WINDOW_MS,
    GLOSS_UTTERANCE_PAUSE_MS,
)

logger = logging.getLogger("gesture-service.gloss_sequence")

STATUS_ACCEPTED = "accepted"
STATUS_UNCERTAIN = "uncertain"

BOUNDARY_PAUSE = "pause"
BOUNDARY_FINALIZE = "finalize"
BOUNDARY_MAX_LENGTH = "max_length"


@dataclass
class GlossToken:
    """One gloss of the sequence with its timing and confidence."""

    gloss: str
    confidence: float
    start_ms: int
    end_ms: int
    status: str
    repeats: int = 1  # how many predictions were merged into this token

    def to_dict(self) -> dict[str, Any]:
        return {
            "gloss": self.gloss,
            "confidence": self.confidence,
            "startMs": self.start_ms,
            "endMs": self.end_ms,
            "status": self.status,
            "repeats": self.repeats,
        }


@dataclass
class GlossSequence:
    """A finished utterance: the structured input for the NLP/LLM layer."""

    session_id: str
    utterance_id: int
    tokens: list[GlossToken]
    # Positions of missing predictions: a gap value g means "one or more
    # segments were not recognized right before tokens[g]" (g == len(tokens)
    # means after the last token).
    gaps: list[int] = field(default_factory=list)
    boundary: str = BOUNDARY_FINALIZE

    @property
    def start_ms(self) -> int:
        return min(t.start_ms for t in self.tokens)

    @property
    def end_ms(self) -> int:
        return max(t.end_ms for t in self.tokens)

    @property
    def gloss_text(self) -> str:
        return " ".join(t.gloss for t in self.tokens)

    def to_message(self) -> dict[str, Any]:
        """The `gloss_sequence` WebSocket message (see the contract)."""
        return {
            "type": "gloss_sequence",
            "sessionId": self.session_id,
            "utteranceId": self.utterance_id,
            "glosses": [t.to_dict() for t in self.tokens],
            "glossText": self.gloss_text,
            "gaps": list(self.gaps),
            "startMs": self.start_ms,
            "endMs": self.end_ms,
            "boundary": self.boundary,
        }


class GlossSequenceProcessor:
    """Per-session processor. One instance lives in each Session."""

    def __init__(
        self,
        session_id: str,
        *,
        min_confidence: float = GLOSS_MIN_CONFIDENCE,
        accept_confidence: float = GLOSS_ACCEPT_CONFIDENCE,
        repeat_window_ms: int = GLOSS_REPEAT_WINDOW_MS,
        pause_ms: int = GLOSS_UTTERANCE_PAUSE_MS,
        max_length: int = GLOSS_MAX_SEQUENCE_LENGTH,
    ) -> None:
        self.session_id = session_id
        self.min_confidence = min_confidence
        self.accept_confidence = accept_confidence
        self.repeat_window_ms = repeat_window_ms
        self.pause_ms = pause_ms
        self.max_length = max_length

        self._utterance_counter = 0
        self._tokens: list[GlossToken] = []
        self._gaps: list[int] = []
        self._last_activity_ms: Optional[int] = None

    @property
    def has_pending(self) -> bool:
        """True while an utterance is open (has tokens or gaps)."""
        return bool(self._tokens or self._gaps)

    # ------------------------------------------------------------------ input

    def add_prediction(
        self, result: Any, start_ms: float, end_ms: float
    ) -> Optional[GlossSequence]:
        """
        Add the classification result of one gesture segment.

        `result` is None (or has no gloss) when the segment was not
        recognized; that is recorded as a gap. Returns a finished
        GlossSequence only if this prediction made the utterance reach the
        maximum length, otherwise None.
        """
        start = int(start_ms)
        end = max(int(end_ms), start)
        if self._last_activity_ms is None or end > self._last_activity_ms:
            self._last_activity_ms = end

        glosses = [g for g in (getattr(result, "gloss", None) or []) if g and g.strip()]
        confidence = float(getattr(result, "confidence", 0.0) or 0.0)

        if not glosses or confidence < self.min_confidence:
            self._add_gap()
            return None

        for gloss in glosses:
            self._add_token(
                GlossToken(
                    gloss=gloss,
                    confidence=round(confidence, 4),
                    start_ms=start,
                    end_ms=end,
                    status=self._status_for(confidence),
                )
            )

        if len(self._tokens) >= self.max_length:
            return self.close(BOUNDARY_MAX_LENGTH)
        return None

    def tick(self, now_ms: float, busy: bool = False) -> Optional[GlossSequence]:
        """
        Call on every incoming frame with its timestamp. Closes the utterance
        when no gesture has been seen for `pause_ms`. `busy` must be True
        while a gesture is still in progress (the spotter is active), so a
        long sign is never cut by the pause rule.
        """
        if busy or not self.has_pending or self._last_activity_ms is None:
            return None
        if int(now_ms) - self._last_activity_ms >= self.pause_ms:
            return self.close(BOUNDARY_PAUSE)
        return None

    # ----------------------------------------------------------------- output

    def close(self, reason: str = BOUNDARY_FINALIZE) -> Optional[GlossSequence]:
        """
        End the current utterance and return it. Returns None when nothing
        was recognized (only gaps, or nothing at all); the state is cleared
        either way.
        """
        tokens, gaps = self._tokens, self._gaps
        self._tokens, self._gaps, self._last_activity_ms = [], [], None
        if not tokens:
            return None

        self._utterance_counter += 1
        sequence = GlossSequence(
            session_id=self.session_id,
            utterance_id=self._utterance_counter,
            tokens=tokens,
            gaps=gaps,
            boundary=reason,
        )
        logger.info(
            "Utterance %d closed (%s): %d glosses, %d gaps: %s",
            sequence.utterance_id,
            reason,
            len(tokens),
            len(gaps),
            sequence.gloss_text,
            extra={"session_id": self.session_id, "audit": True},
        )
        return sequence

    def discard(self) -> None:
        """Drop the open utterance without emitting it (session reset)."""
        self._tokens, self._gaps, self._last_activity_ms = [], [], None

    # --------------------------------------------------------------- internal

    def _status_for(self, confidence: float) -> str:
        return STATUS_ACCEPTED if confidence >= self.accept_confidence else STATUS_UNCERTAIN

    def _add_gap(self) -> None:
        position = len(self._tokens)
        if not self._gaps or self._gaps[-1] != position:
            self._gaps.append(position)  # one gap marker per position

    def _add_token(self, token: GlossToken) -> None:
        last = self._tokens[-1] if self._tokens else None
        if (
            last is not None
            and last.gloss == token.gloss
            and token.start_ms - last.end_ms <= self.repeat_window_ms
        ):
            # Repeated prediction of the same sign: merge it into one token.
            last.start_ms = min(last.start_ms, token.start_ms)
            last.end_ms = max(last.end_ms, token.end_ms)
            last.repeats += 1
            if token.confidence > last.confidence:
                last.confidence = token.confidence
                last.status = self._status_for(token.confidence)
            return

        # Keep temporal order even if a prediction arrives late.
        position = len(self._tokens)
        while position > 0 and self._tokens[position - 1].start_ms > token.start_ms:
            position -= 1
        self._tokens.insert(position, token)
        self._gaps = [g + 1 if g > position else g for g in self._gaps]
