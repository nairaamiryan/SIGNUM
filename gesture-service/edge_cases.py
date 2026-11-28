"""
Edge Cases and Error Recovery (KAN-27).

Detects and recovers from environmental and functional edge cases so that
corrupted or misleading text is never presented as a valid recognition
result:
  * Severe motion blur (implausible inter-frame velocity spikes)
  * Partial hand/body occlusion (sustained degraded/bad frames)
  * User moving outside the active camera area
  * Multiple people or extraneous hands (spatial plausibility + client hints)
  * False triggers from non-signing / fidgeting movements
  * Poor illumination (via client luminance hints)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from constants import (
    EDGE_BLUR_STREAK_TO_WARN,
    EDGE_MAX_HAND_SHOULDER_DISTANCE,
    EDGE_MIN_GOOD_FRAME_RATIO,
    EDGE_MIN_NET_DISPLACEMENT,
    EDGE_OCCLUSION_STREAK_TO_WARN,
    EDGE_OUT_OF_FRAME_STREAK_TO_WARN,
    EDGE_SEVERE_BLUR_MOTION_THRESHOLD,
    EDGE_WARNING_COOLDOWN_MS,
)
from continuous import FrameQuality, assess_frame_quality
from landmark_buffer import LandmarkFrame
from lifecycle import POSE_LEFT_SHOULDER, POSE_RIGHT_SHOULDER, assess_signer_positioning
from spotting import frame_motion_intensity, is_neutral_pose


class EdgeWarningCode(str, Enum):
    """Machine-readable edge-case warning codes shared with the frontend."""

    CAMERA_DISCONNECTED = "camera_disconnected"
    POOR_ILLUMINATION = "poor_illumination"
    SEVERE_MOTION_BLUR = "severe_motion_blur"
    PARTIAL_OCCLUSION = "partial_occlusion"
    USER_OUT_OF_FRAME = "user_out_of_frame"
    MULTIPLE_PEOPLE = "multiple_people"
    EXTRANEOUS_HANDS = "extraneous_hands"
    NON_SIGNING_MOVEMENT = "non_signing_movement"
    NETWORK_INTERRUPTED = "network_interrupted"
    SERVICE_ERROR = "service_error"


@dataclass(frozen=True)
class EdgeWarning:
    """A throttled edge-case warning emitted to the client."""

    code: EdgeWarningCode
    recoverable: bool = True

    def to_message(self) -> dict:
        return {
            "type": "warning",
            "code": self.code.value,
            "recoverable": self.recoverable,
        }


def is_hand_extraneous(
    hand: Optional[list[dict]],
    pose: Optional[list[dict]],
    max_distance: float = EDGE_MAX_HAND_SHOULDER_DISTANCE,
) -> bool:
    """Return True if a detected hand is implausibly far from the primary
    signer's shoulder center (likely an extraneous hand from another person)."""
    if not hand or not pose or len(pose) <= POSE_RIGHT_SHOULDER:
        return False
    left_sh = pose[POSE_LEFT_SHOULDER]
    right_sh = pose[POSE_RIGHT_SHOULDER]
    sh_x = (float(left_sh["x"]) + float(right_sh["x"])) / 2.0
    sh_y = (float(left_sh["y"]) + float(right_sh["y"])) / 2.0
    wrist = hand[0]
    dist = math.hypot(float(wrist["x"]) - sh_x, float(wrist["y"]) - sh_y)
    return dist > max_distance


def is_non_signing_movement(
    frames: list[LandmarkFrame],
    min_net_displacement: float = EDGE_MIN_NET_DISPLACEMENT,
) -> bool:
    """Detect false triggers caused by non-signing movements (micro-jitter,
    fidgeting, or neutral-posture motion with negligible net displacement)."""
    if len(frames) < 2:
        return True

    if all(is_neutral_pose(f) for f in frames):
        return True

    def _hand_net_displacement(getter) -> float:
        pts = [getter(f) for f in frames if getter(f)]
        if len(pts) < 2:
            return 0.0
        first, last = pts[0][0], pts[-1][0]
        max_spread = 0.0
        for p in pts[1:]:
            d = math.hypot(float(p[0]["x"]) - float(first["x"]), float(p[0]["y"]) - float(first["y"]))
            if d > max_spread:
                max_spread = d
        end_disp = math.hypot(
            float(last["x"]) - float(first["x"]), float(last["y"]) - float(first["y"])
        )
        return max(max_spread, end_disp)

    left_disp = _hand_net_displacement(lambda f: f.left_hand)
    right_disp = _hand_net_displacement(lambda f: f.right_hand)
    return max(left_disp, right_disp) < min_net_displacement


class EdgeCaseGuard:
    """Per-session edge-case detector and recovery guard."""

    def __init__(self, cooldown_ms: int = EDGE_WARNING_COOLDOWN_MS) -> None:
        self._cooldown_ms = cooldown_ms
        self.reset()

    def reset(self) -> None:
        self._prev_frame: Optional[LandmarkFrame] = None
        self._blur_streak: int = 0
        self._occlusion_streak: int = 0
        self._out_of_frame_streak: int = 0
        self._last_warned_ms: dict[EdgeWarningCode, int] = {}

    def _can_warn(self, code: EdgeWarningCode, ts: int) -> bool:
        last = self._last_warned_ms.get(code)
        if last is None or (ts - last) >= self._cooldown_ms:
            self._last_warned_ms[code] = ts
            return True
        return False

    def inspect_frame(
        self,
        frame: LandmarkFrame,
        *,
        multiple_people: bool = False,
        extraneous_hands: bool = False,
        poor_illumination: bool = False,
    ) -> tuple[bool, list[EdgeWarning]]:
        """Inspect an incoming frame for environmental/tracking edge cases.

        Returns ``(should_suppress_frame, warnings)``. When
        ``should_suppress_frame`` is True (e.g. multiple people or severe
        blur spike), the caller should avoid feeding the corrupted frame
        into classification so misleading text is not produced.
        """
        ts = int(frame.timestamp)
        warnings: list[EdgeWarning] = []
        suppress = False

        if poor_illumination and self._can_warn(EdgeWarningCode.POOR_ILLUMINATION, ts):
            warnings.append(EdgeWarning(EdgeWarningCode.POOR_ILLUMINATION))

        if multiple_people:
            suppress = True
            if self._can_warn(EdgeWarningCode.MULTIPLE_PEOPLE, ts):
                warnings.append(EdgeWarning(EdgeWarningCode.MULTIPLE_PEOPLE))

        # Check client hint or spatial plausibility for extraneous hands
        spatial_extraneous = is_hand_extraneous(frame.left_hand, frame.pose) or is_hand_extraneous(
            frame.right_hand, frame.pose
        )
        if extraneous_hands or spatial_extraneous:
            suppress = True
            if self._can_warn(EdgeWarningCode.EXTRANEOUS_HANDS, ts):
                warnings.append(EdgeWarning(EdgeWarningCode.EXTRANEOUS_HANDS))

        # Check user positioning in active camera area
        present, positioned = assess_signer_positioning(frame)
        if present and not positioned:
            self._out_of_frame_streak += 1
            if self._out_of_frame_streak >= EDGE_OUT_OF_FRAME_STREAK_TO_WARN:
                if self._can_warn(EdgeWarningCode.USER_OUT_OF_FRAME, ts):
                    warnings.append(EdgeWarning(EdgeWarningCode.USER_OUT_OF_FRAME))
        else:
            self._out_of_frame_streak = 0

        # Severe motion blur detection (velocity spike)
        if self._prev_frame is not None:
            motion = frame_motion_intensity(self._prev_frame, frame)
            if motion > EDGE_SEVERE_BLUR_MOTION_THRESHOLD:
                self._blur_streak += 1
                suppress = True
                if self._blur_streak >= EDGE_BLUR_STREAK_TO_WARN:
                    if self._can_warn(EdgeWarningCode.SEVERE_MOTION_BLUR, ts):
                        warnings.append(EdgeWarning(EdgeWarningCode.SEVERE_MOTION_BLUR))
            else:
                self._blur_streak = 0
        self._prev_frame = frame

        # Partial occlusion / tracking loss
        quality = assess_frame_quality(frame)
        if quality in (FrameQuality.BAD, FrameQuality.DEGRADED):
            self._occlusion_streak += 1
            if self._occlusion_streak >= EDGE_OCCLUSION_STREAK_TO_WARN:
                if self._can_warn(EdgeWarningCode.PARTIAL_OCCLUSION, ts):
                    warnings.append(EdgeWarning(EdgeWarningCode.PARTIAL_OCCLUSION))
        else:
            self._occlusion_streak = 0

        return suppress, warnings

    def validate_segment(
        self,
        frames: list[LandmarkFrame],
        quality_scores: Optional[list[FrameQuality]] = None,
    ) -> tuple[bool, Optional[EdgeWarning]]:
        """Validate a spotted segment before classification.

        Prevents corrupted segments (excessive occlusion/blur) or false
        triggers (non-signing fidgeting) from producing misleading text.
        """
        if not frames:
            return False, None

        ts = int(frames[-1].timestamp)
        scores = quality_scores or [assess_frame_quality(f) for f in frames]
        good_count = sum(1 for q in scores if q == FrameQuality.GOOD)
        degraded_count = sum(1 for q in scores if q == FrameQuality.DEGRADED)
        usable_ratio = (good_count + 0.5 * degraded_count) / len(scores)

        if usable_ratio < EDGE_MIN_GOOD_FRAME_RATIO:
            warn = (
                EdgeWarning(EdgeWarningCode.PARTIAL_OCCLUSION)
                if self._can_warn(EdgeWarningCode.PARTIAL_OCCLUSION, ts)
                else None
            )
            return False, warn

        if is_non_signing_movement(frames):
            warn = (
                EdgeWarning(EdgeWarningCode.NON_SIGNING_MOVEMENT)
                if self._can_warn(EdgeWarningCode.NON_SIGNING_MOVEMENT, ts)
                else None
            )
            return False, warn

        return True, None
