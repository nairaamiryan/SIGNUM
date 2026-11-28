"""
Gesture Lifecycle Management (KAN-26).

Tracks and manages the full lifecycle of a signing sequence from start
to completion:
  * Start of signing (signer appearance and positioning in active camera area)
  * Active signing / progression
  * Inactivity periods (motion cessation, neutral posture, or signer leaving)
  * End of signing and automatic sentence finalization
  * Manual sentence finalization (`finalize`) and termination (`restart`)

All timeouts and thresholds are configurable via ``LifecycleConfig``
(populated from ``constants.py`` and environment variables) so they can
be adjusted empirically during testing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from constants import (
    LIFECYCLE_ACTIVE_AREA_MARGIN,
    LIFECYCLE_FINALIZE_TIMEOUT_MS,
    LIFECYCLE_INACTIVITY_MS,
    LIFECYCLE_MIN_SHOULDER_SPAN,
    LIFECYCLE_NEUTRAL_END_FRAMES,
    LIFECYCLE_START_HOLD_MS,
)
from landmark_buffer import LandmarkFrame
from spotting import is_neutral_pose

# MediaPipe Pose indices for upper-body positioning checks.
POSE_LEFT_SHOULDER = 11
POSE_RIGHT_SHOULDER = 12


class LifecyclePhase(str, Enum):
    """Shared lifecycle phases synchronized between backend and frontend."""

    IDLE = "idle"  # No signer positioned in active camera area
    READY = "ready"  # Signer positioned in active area, ready to sign
    SIGNING = "signing"  # Active signing / progression in progress
    INACTIVE = "inactive"  # Inactivity period detected after signing
    FINALIZING = "finalizing"  # Sentence finalization in progress
    TERMINATED = "terminated"  # Manual sentence termination


@dataclass(frozen=True)
class LifecycleConfig:
    """Empirically adjustable thresholds for gesture lifecycle detection."""

    active_area_margin: float = LIFECYCLE_ACTIVE_AREA_MARGIN
    min_shoulder_span: float = LIFECYCLE_MIN_SHOULDER_SPAN
    start_hold_ms: int = LIFECYCLE_START_HOLD_MS
    inactivity_ms: int = LIFECYCLE_INACTIVITY_MS
    finalize_timeout_ms: int = LIFECYCLE_FINALIZE_TIMEOUT_MS
    neutral_end_frames: int = LIFECYCLE_NEUTRAL_END_FRAMES

    @classmethod
    def from_env(cls) -> LifecycleConfig:
        """Load lifecycle configuration from environment variables."""
        return cls(
            active_area_margin=float(
                os.environ.get("LIFECYCLE_ACTIVE_AREA_MARGIN", str(LIFECYCLE_ACTIVE_AREA_MARGIN))
            ),
            min_shoulder_span=float(
                os.environ.get("LIFECYCLE_MIN_SHOULDER_SPAN", str(LIFECYCLE_MIN_SHOULDER_SPAN))
            ),
            start_hold_ms=int(
                os.environ.get("LIFECYCLE_START_HOLD_MS", str(LIFECYCLE_START_HOLD_MS))
            ),
            inactivity_ms=int(
                os.environ.get("LIFECYCLE_INACTIVITY_MS", str(LIFECYCLE_INACTIVITY_MS))
            ),
            finalize_timeout_ms=int(
                os.environ.get("LIFECYCLE_FINALIZE_TIMEOUT_MS", str(LIFECYCLE_FINALIZE_TIMEOUT_MS))
            ),
            neutral_end_frames=int(
                os.environ.get("LIFECYCLE_NEUTRAL_END_FRAMES", str(LIFECYCLE_NEUTRAL_END_FRAMES))
            ),
        )


@dataclass(frozen=True)
class LifecycleUpdate:
    """Result of a lifecycle evaluation step."""

    phase: LifecyclePhase
    previous_phase: LifecyclePhase
    changed: bool
    reason: str
    signer_present: bool
    signer_positioned: bool
    inactivity_ms: int
    should_finalize: bool = False

    def to_message(self, session_id: str) -> dict[str, Any]:
        """Serialize as the `lifecycle` WebSocket message."""
        return {
            "type": "lifecycle",
            "sessionId": session_id,
            "phase": self.phase.value,
            "reason": self.reason,
            "signerPresent": self.signer_present,
            "signerPositioned": self.signer_positioned,
            "inactivityMs": self.inactivity_ms,
        }


def _point_in_active_area(point: dict, margin: float) -> bool:
    x = float(point.get("x", -1.0))
    y = float(point.get("y", -1.0))
    return margin <= x <= (1.0 - margin) and margin <= y <= (1.0 - margin)


def assess_signer_positioning(
    frame: LandmarkFrame,
    *,
    margin: float = LIFECYCLE_ACTIVE_AREA_MARGIN,
    min_shoulder_span: float = LIFECYCLE_MIN_SHOULDER_SPAN,
) -> tuple[bool, bool]:
    """Determine ``(signer_present, signer_positioned)`` for a frame.

    * ``signer_present`` is True when at least one hand or upper-body pose is
      detected in the frame.
    * ``signer_positioned`` is True when the signer appears within the active
      camera area (shoulders within ``margin`` bounds and separated by at least
      ``min_shoulder_span``, or if pose is unavailable, visible hand landmarks
      inside the active area).
    """
    has_left = bool(frame.left_hand)
    has_right = bool(frame.right_hand)
    pose = frame.pose
    has_shoulders = bool(pose and len(pose) > POSE_RIGHT_SHOULDER)

    signer_present = has_left or has_right or has_shoulders
    if not signer_present:
        return False, False

    if has_shoulders and pose is not None:
        left_sh = pose[POSE_LEFT_SHOULDER]
        right_sh = pose[POSE_RIGHT_SHOULDER]
        span = abs(float(right_sh["x"]) - float(left_sh["x"]))
        in_bounds = _point_in_active_area(left_sh, margin) and _point_in_active_area(
            right_sh, margin
        )
        return True, in_bounds and span >= min_shoulder_span

    # Fallback when pose landmarks are absent: check visible hand centroids.
    for hand in (frame.left_hand, frame.right_hand):
        if hand:
            cx = sum(float(p["x"]) for p in hand) / len(hand)
            cy = sum(float(p["y"]) for p in hand) / len(hand)
            if _point_in_active_area({"x": cx, "y": cy}, margin):
                return True, True

    return True, False


class GestureLifecycleManager:
    """Manages the signing sequence lifecycle for one recognition session."""

    def __init__(self, config: Optional[LifecycleConfig] = None) -> None:
        self.config = config or LifecycleConfig.from_env()
        self.reset()

    def reset(self) -> None:
        self._phase: LifecyclePhase = LifecyclePhase.IDLE
        self._reason: str = "session_reset"
        self._signer_present: bool = False
        self._signer_positioned: bool = False
        self._positioned_since_ms: Optional[int] = None
        self._last_active_ms: Optional[int] = None
        self._inactivity_ms: int = 0
        self._neutral_run: int = 0
        self._finalized_for_idle_run: bool = False

    @property
    def phase(self) -> LifecyclePhase:
        return self._phase

    @property
    def signer_present(self) -> bool:
        return self._signer_present

    @property
    def signer_positioned(self) -> bool:
        return self._signer_positioned

    def current_update(self, *, changed: bool = False) -> LifecycleUpdate:
        return LifecycleUpdate(
            phase=self._phase,
            previous_phase=self._phase,
            changed=changed,
            reason=self._reason,
            signer_present=self._signer_present,
            signer_positioned=self._signer_positioned,
            inactivity_ms=self._inactivity_ms,
            should_finalize=False,
        )

    def on_frame(
        self,
        frame: LandmarkFrame,
        *,
        spotter_active: bool,
        has_pending_glosses: bool,
    ) -> LifecycleUpdate:
        """Advance lifecycle state from an incoming landmark frame."""
        prev = self._phase
        ts = int(frame.timestamp)
        present, positioned = assess_signer_positioning(
            frame,
            margin=self.config.active_area_margin,
            min_shoulder_span=self.config.min_shoulder_span,
        )
        self._signer_present = present
        self._signer_positioned = positioned

        neutral = is_neutral_pose(frame)
        self._neutral_run = self._neutral_run + 1 if neutral else 0

        if positioned:
            if self._positioned_since_ms is None:
                self._positioned_since_ms = ts
        else:
            self._positioned_since_ms = None

        is_actively_signing = spotter_active and positioned and not neutral
        should_finalize = False

        if is_actively_signing:
            self._last_active_ms = ts
            self._inactivity_ms = 0
            self._finalized_for_idle_run = False
            self._transition(LifecyclePhase.SIGNING, "active_signing")
        elif self._phase in (LifecyclePhase.SIGNING, LifecyclePhase.INACTIVE):
            if self._last_active_ms is None:
                self._last_active_ms = ts
            self._inactivity_ms = max(0, ts - self._last_active_ms)

            neutral_ended = self._neutral_run >= self.config.neutral_end_frames
            timed_out = self._inactivity_ms >= self.config.finalize_timeout_ms
            left_area = not present

            if (timed_out or (neutral_ended and has_pending_glosses) or (left_area and timed_out)):
                if has_pending_glosses and not self._finalized_for_idle_run:
                    should_finalize = True
                    self._finalized_for_idle_run = True
                    reason = "neutral_posture" if neutral_ended else "inactivity_timeout"
                    self._transition(LifecyclePhase.FINALIZING, reason)
                elif not positioned:
                    self._transition(LifecyclePhase.IDLE, "signer_left_area")
                else:
                    self._transition(LifecyclePhase.READY, "inactivity_reset")
            elif self._inactivity_ms >= self.config.inactivity_ms or neutral_ended or not positioned:
                reason = (
                    "signer_out_of_area"
                    if not positioned
                    else ("neutral_posture" if neutral_ended else "inactivity_period")
                )
                self._transition(LifecyclePhase.INACTIVE, reason)
        elif self._phase == LifecyclePhase.FINALIZING:
            # Return to READY/IDLE once the finalized cycle moves forward.
            self._inactivity_ms = 0
            pos_since = (
                self._positioned_since_ms if self._positioned_since_ms is not None else ts
            )
            if positioned and (ts - pos_since >= self.config.start_hold_ms):
                self._transition(LifecyclePhase.READY, "ready_for_next_sentence")
            elif not positioned:
                self._transition(LifecyclePhase.IDLE, "awaiting_signer")
        elif self._phase == LifecyclePhase.TERMINATED:
            self._inactivity_ms = 0
            if positioned:
                self._transition(LifecyclePhase.READY, "ready_after_termination")
            else:
                self._transition(LifecyclePhase.IDLE, "awaiting_signer")
        else:
            # IDLE or READY
            self._inactivity_ms = 0
            if positioned:
                pos_since = (
                    self._positioned_since_ms if self._positioned_since_ms is not None else ts
                )
                held_ms = ts - pos_since
                if held_ms >= self.config.start_hold_ms:
                    if has_pending_glosses:
                        self._last_active_ms = ts
                        self._transition(LifecyclePhase.SIGNING, "signing_progression")
                    else:
                        self._transition(LifecyclePhase.READY, "signer_positioned")
            else:
                self._transition(LifecyclePhase.IDLE, "signer_not_positioned")

        return LifecycleUpdate(
            phase=self._phase,
            previous_phase=prev,
            changed=self._phase != prev,
            reason=self._reason,
            signer_present=self._signer_present,
            signer_positioned=self._signer_positioned,
            inactivity_ms=self._inactivity_ms,
            should_finalize=should_finalize,
        )

    def on_manual_finalize(self) -> LifecycleUpdate:
        """Transition to FINALIZING on explicit user finalize action."""
        prev = self._phase
        self._transition(LifecyclePhase.FINALIZING, "manual_finalize")
        return LifecycleUpdate(
            phase=self._phase,
            previous_phase=prev,
            changed=self._phase != prev,
            reason=self._reason,
            signer_present=self._signer_present,
            signer_positioned=self._signer_positioned,
            inactivity_ms=self._inactivity_ms,
            should_finalize=True,
        )

    def on_finalized(self) -> LifecycleUpdate:
        """Complete sentence finalization and return to READY or IDLE."""
        prev = self._phase
        self._last_active_ms = None
        self._inactivity_ms = 0
        self._finalized_for_idle_run = False
        next_phase = LifecyclePhase.READY if self._signer_positioned else LifecyclePhase.IDLE
        self._transition(next_phase, "sentence_finalized")
        return LifecycleUpdate(
            phase=self._phase,
            previous_phase=prev,
            changed=self._phase != prev,
            reason=self._reason,
            signer_present=self._signer_present,
            signer_positioned=self._signer_positioned,
            inactivity_ms=0,
            should_finalize=False,
        )

    def on_manual_terminate(self) -> LifecycleUpdate:
        """Transition to TERMINATED on explicit user restart/termination."""
        prev = self._phase
        self._last_active_ms = None
        self._inactivity_ms = 0
        self._neutral_run = 0
        self._finalized_for_idle_run = False
        self._transition(LifecyclePhase.TERMINATED, "manual_termination")
        return LifecycleUpdate(
            phase=self._phase,
            previous_phase=prev,
            changed=self._phase != prev,
            reason=self._reason,
            signer_present=self._signer_present,
            signer_positioned=self._signer_positioned,
            inactivity_ms=0,
            should_finalize=False,
        )

    def _transition(self, new_phase: LifecyclePhase, reason: str) -> None:
        self._phase = new_phase
        self._reason = reason
