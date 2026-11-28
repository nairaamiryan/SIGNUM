"""
Sentence generation (KAN-19): from an ordered gloss sequence to a coherent
Armenian sentence, with a processing status.

Pipeline for one utterance:
  gloss sequence -> prompt -> LLMProvider -> parse -> validate -> SentenceResult

The generator knows nothing about gesture recognition or about a concrete LLM:
it receives any object shaped like a GlossSequence and talks to any
LLMProvider. Statuses:

  ok        sentence generated from a clean sequence
  partial   sentence generated, but the input had gaps, uncertain glosses, or
            the model left glosses out (the sentence may be incomplete)
  fallback  no usable sentence: the glosses are returned as plain text and
            `warnings` says why (LLM not configured, timeout, invalid output)
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Sequence

from constants import NLP_CONTEXT_SENTENCES, NLP_MAX_WORDS_PER_GLOSS
from nlp.prompt import SYSTEM_PROMPT, build_user_prompt
from nlp.providers import LLMError, LLMProvider, build_provider

logger = logging.getLogger("gesture-service.nlp")

ARMENIAN_FIRST = "Ա"
ARMENIAN_LAST = "֏"
_MIN_ARMENIAN_RATIO = 0.8


class SentenceStatus(str, Enum):
    OK = "ok"
    PARTIAL = "partial"
    FALLBACK = "fallback"


@dataclass
class SentenceResult:
    session_id: str
    utterance_id: int
    text: str
    status: SentenceStatus
    gloss_text: str
    warnings: list[str] = field(default_factory=list)
    provider: Optional[str] = None
    model: Optional[str] = None
    latency_ms: int = 0

    def to_message(self) -> dict[str, Any]:
        """The `sentence` WebSocket message (see the contract)."""
        return {
            "type": "sentence",
            "sessionId": self.session_id,
            "utteranceId": self.utterance_id,
            "text": self.text,
            "status": self.status.value,
            "glossText": self.gloss_text,
            "warnings": list(self.warnings),
            "provider": self.provider,
            "model": self.model,
            "latencyMs": self.latency_ms,
        }


class NLPService:
    def __init__(
        self,
        provider: Optional[LLMProvider],
        *,
        context_sentences: int = NLP_CONTEXT_SENTENCES,
        max_words_per_gloss: int = NLP_MAX_WORDS_PER_GLOSS,
    ) -> None:
        self.provider = provider
        self.context_sentences = context_sentences
        self.max_words_per_gloss = max_words_per_gloss

    @classmethod
    def from_env(cls) -> "NLPService":
        return cls(build_provider())

    async def generate(self, sequence: Any, context: Sequence[str] = ()) -> SentenceResult:
        """Async wrapper: the provider call blocks, so it runs in a worker
        thread and never stalls the WebSocket loop."""
        return await asyncio.to_thread(self.generate_sync, sequence, list(context))

    def generate_sync(self, sequence: Any, context: Sequence[str] = ()) -> SentenceResult:
        started = time.monotonic()
        tokens = list(sequence.tokens)
        glosses = [t.gloss for t in tokens]
        gloss_text = " ".join(glosses)

        warnings: list[str] = []
        if sequence.gaps:
            warnings.append("missing_glosses")
        if any(t.status == "uncertain" for t in tokens):
            warnings.append("uncertain_glosses")
        if any(t.status == "ambiguous" for t in tokens):
            warnings.append("ambiguous_glosses")

        def result(text: str, status: SentenceStatus, extra: Sequence[str] = ()) -> SentenceResult:
            return SentenceResult(
                session_id=sequence.session_id,
                utterance_id=sequence.utterance_id,
                text=text,
                status=status,
                gloss_text=gloss_text,
                warnings=warnings + [w for w in extra if w not in warnings],
                provider=getattr(self.provider, "name", None),
                model=getattr(self.provider, "model", None),
                latency_ms=int((time.monotonic() - started) * 1000),
            )

        if self.provider is None:
            return result(gloss_text, SentenceStatus.FALLBACK, ["llm_not_configured"])

        recent = list(context)[-self.context_sentences :] if self.context_sentences > 0 else []
        user_prompt = build_user_prompt(tokens, sequence.gaps, recent)

        try:
            raw = self.provider.generate(SYSTEM_PROMPT, user_prompt)
            sentence, complete, omitted = self._parse(raw)
            self._validate(sentence, glosses, self.max_words_per_gloss)
        except LLMError as exc:
            logger.warning(
                "LLM call failed for utterance %s: %s",
                sequence.utterance_id,
                exc.code,
                extra={"session_id": sequence.session_id},
            )
            return result(gloss_text, SentenceStatus.FALLBACK, [f"llm_{exc.code}"])
        except ValueError as exc:
            logger.warning(
                "LLM output rejected for utterance %s: %s",
                sequence.utterance_id,
                exc,
                extra={"session_id": sequence.session_id},
            )
            return result(gloss_text, SentenceStatus.FALLBACK, ["invalid_output"])

        extra: list[str] = []
        if omitted:
            extra.append("omitted_glosses")
        if not complete:
            extra.append("incomplete")
        status = SentenceStatus.PARTIAL if (warnings or extra) else SentenceStatus.OK

        final = result(sentence, status, extra)
        logger.info(
            "Sentence generated (%s) for utterance %s: %s",
            status.value,
            sequence.utterance_id,
            sentence,
            extra={"session_id": sequence.session_id, "audit": True},
        )
        return final

    # ------------------------------------------------------------- internals

    @staticmethod
    def _parse(raw: str) -> tuple[str, bool, list[str]]:
        text = raw.strip()
        fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fenced:
            text = fenced.group(1)
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ValueError("answer is not valid JSON") from exc
        if not isinstance(data, dict) or not isinstance(data.get("sentence"), str):
            raise ValueError("answer has no 'sentence' string")

        complete = data.get("complete", True)
        if not isinstance(complete, bool):
            complete = True
        omitted = data.get("omitted") or []
        if not isinstance(omitted, list):
            omitted = []
        return data["sentence"].strip(), complete, [str(o) for o in omitted]

    @staticmethod
    def _validate(sentence: str, glosses: Sequence[str], max_words_per_gloss: int) -> None:
        """Cheap guards against output that does not belong to the input."""
        if not sentence:
            raise ValueError("empty sentence")

        letters = [c for c in sentence if c.isalpha()]
        armenian = [c for c in letters if ARMENIAN_FIRST <= c <= ARMENIAN_LAST]
        if not letters or len(armenian) / len(letters) < _MIN_ARMENIAN_RATIO:
            raise ValueError("sentence is not written in Armenian")

        if any(c.isdigit() for c in sentence) and not any(c.isdigit() for g in glosses for c in g):
            raise ValueError("sentence contains digits that are not in the glosses")

        if len(sentence.split()) > max_words_per_gloss * max(len(glosses), 1) + 4:
            raise ValueError("sentence is much longer than the glosses justify")
