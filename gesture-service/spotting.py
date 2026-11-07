"""
Gesture spotting (segmentation).

Two layers live in this module:

1. Stateless helpers (is_segment_active / is_segment_idle) that look at the
   buffered frames. They are kept because main.py still imports them.

2. HeuristicGestureSpotter - a small state machine that consumes landmark
   frames one by one and emits finished gesture segments:

      IDLE --(MIN_ACTIVE_FRAMES frames above MOTION_THRESHOLD)--> ACTIVE
      ACTIVE --(IDLE_FRAMES_TO_END_SEGMENT frames below END_MOTION_THRESHOLD)--> IDLE

   Start and end use different thresholds (hysteresis), so noise around a single
   threshold does not chop a gesture into pieces. Inside an ACTIVE segment a deep
   local minimum of the motion curve (the hand slows down between two signs) splits
   the segment, which handles co-articulation: consecutive signs without a pause.

   The GestureSpotter protocol is the extension point for a learned model: any
   class with the same process / flush / reset methods can replace the heuristic.
"""

from dataclasses import dataclass
from enum import Enum
from collections import deque
from typing import Optional, Protocol

from landmark_buffer import LandmarkFrame
from constants import (
    MOTION_THRESHOLD,
    END_MOTION_THRESHOLD,
    MIN_ACTIVE_FRAMES,
    IDLE_FRAMES_TO_END_SEGMENT,
    PRE_ROLL_FRAMES,
    COARTICULATION_MIN_SEGMENT_FRAMES,
    COARTICULATION_DIP_RATIO,
    SEGMENT_MAX_FRAMES,
)


def _hand_motion(prev: list[dict] | None, curr: list[dict] | None) -> float:
    """Average per-point displacement between two hand landmark sets.
    Returns 0 if either frame has no hand detected."""
    if not prev or not curr or len(prev) != len(curr):
        return 0.0

    total = 0.0
    for p, c in zip(prev, curr):
        total += abs(c["x"] - p["x"]) + abs(c["y"] - p["y"]) + abs(c["z"] - p["z"])
    return total / len(prev)


def frame_motion_intensity(prev: LandmarkFrame, curr: LandmarkFrame) -> float:
    """Combined motion intensity across both hands between two frames."""
    left = _hand_motion(prev.left_hand, curr.left_hand)
    right = _hand_motion(prev.right_hand, curr.right_hand)
    return max(left, right)


def is_segment_active(frames: list[LandmarkFrame]) -> bool:
    """True once at least MIN_ACTIVE_FRAMES consecutive recent frames show
    motion above MOTION_THRESHOLD."""
    if len(frames) < MIN_ACTIVE_FRAMES + 1:
        return False

    active_streak = 0
    for i in range(len(frames) - 1, 0, -1):
        intensity = frame_motion_intensity(frames[i - 1], frames[i])
        if intensity >= MOTION_THRESHOLD:
            active_streak += 1
            if active_streak >= MIN_ACTIVE_FRAMES:
                return True
        else:
            break

    return False


def is_segment_idle(frames: list[LandmarkFrame]) -> bool:
    """True when the most recent IDLE_FRAMES_TO_END_SEGMENT frames all show
    low motion, i.e. the signer returned to rest."""
    if len(frames) < IDLE_FRAMES_TO_END_SEGMENT + 1:
        return False

    for i in range(len(frames) - 1, len(frames) - 1 - IDLE_FRAMES_TO_END_SEGMENT, -1):
        intensity = frame_motion_intensity(frames[i - 1], frames[i])
        if intensity >= MOTION_THRESHOLD:
            return False

    return True


# --- Neutral (rest) posture -------------------------------------------------
# Indices of the 33-point MediaPipe pose model. Image y grows downwards, so a
# wrist "below" the hip line has a larger y value.
POSE_LEFT_WRIST = 15
POSE_RIGHT_WRIST = 16
POSE_LEFT_HIP = 23
POSE_RIGHT_HIP = 24


def is_neutral_pose(frame: LandmarkFrame) -> bool:
    """True when both wrists hang below the hips (arms down, resting).
    Movement in that posture is not signing. If pose landmarks are missing,
    the frame is not treated as neutral."""
    pose = frame.pose
    if not pose or len(pose) <= POSE_RIGHT_HIP:
        return False
    hip_y = (pose[POSE_LEFT_HIP]["y"] + pose[POSE_RIGHT_HIP]["y"]) / 2
    return pose[POSE_LEFT_WRIST]["y"] > hip_y and pose[POSE_RIGHT_WRIST]["y"] > hip_y


# --- Segment + spotter interface -------------------------------------------
class SegmentReason(str, Enum):
    IDLE = "idle"                      # signer returned to rest
    COARTICULATION = "coarticulation"  # split at a motion minimum between two signs
    MAX_LENGTH = "max_length"          # segment hit SEGMENT_MAX_FRAMES
    FLUSH = "flush"                    # closed on request (e.g. finalize)


@dataclass
class Segment:
    frames: list[LandmarkFrame]
    reason: SegmentReason

    def __len__(self) -> int:
        return len(self.frames)

    @property
    def start_timestamp(self) -> int:
        return self.frames[0].timestamp

    @property
    def end_timestamp(self) -> int:
        return self.frames[-1].timestamp


class GestureSpotter(Protocol):
    """Extension point: replace the heuristic with a learned model by
    implementing these three methods."""

    def process(self, frame: LandmarkFrame) -> list[Segment]: ...
    def flush(self) -> Optional[Segment]: ...
    def reset(self) -> None: ...


class _State(Enum):
    IDLE = "idle"
    ACTIVE = "active"


class HeuristicGestureSpotter:
    """Motion based spotter (see module docstring). One instance per session."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._state = _State.IDLE
        self._prev: Optional[LandmarkFrame] = None
        self._pre_roll: deque[LandmarkFrame] = deque(maxlen=PRE_ROLL_FRAMES)
        self._cand_frames: list[LandmarkFrame] = []
        self._cand_motion: list[float] = []
        self._frames: list[LandmarkFrame] = []
        self._motion: list[float] = []
        self._idle_run = 0

    @property
    def is_active(self) -> bool:
        return self._state is _State.ACTIVE

    def _frame_motion(self, frame: LandmarkFrame) -> float:
        if self._prev is None or is_neutral_pose(frame):
            return 0.0
        return frame_motion_intensity(self._prev, frame)

    def process(self, frame: LandmarkFrame) -> list[Segment]:
        motion = self._frame_motion(frame)
        self._prev = frame

        if self._state is _State.IDLE:
            self._process_idle(frame, motion)
            return []
        return self._process_active(frame, motion)

    def _process_idle(self, frame: LandmarkFrame, motion: float) -> None:
        if motion >= MOTION_THRESHOLD:
            self._cand_frames.append(frame)
            self._cand_motion.append(motion)
            if len(self._cand_frames) >= MIN_ACTIVE_FRAMES:
                pre = list(self._pre_roll)
                self._frames = pre + self._cand_frames
                self._motion = [0.0] * len(pre) + self._cand_motion
                self._cand_frames, self._cand_motion = [], []
                self._pre_roll.clear()
                self._idle_run = 0
                self._state = _State.ACTIVE
        else:
            self._cand_frames, self._cand_motion = [], []
            self._pre_roll.append(frame)

    def _process_active(self, frame: LandmarkFrame, motion: float) -> list[Segment]:
        self._frames.append(frame)
        self._motion.append(motion)
        self._idle_run = self._idle_run + 1 if motion < END_MOTION_THRESHOLD else 0

        if self._idle_run >= IDLE_FRAMES_TO_END_SEGMENT:
            # Drop the resting tail but keep one frame so the segment ends cleanly.
            keep = len(self._frames) - self._idle_run + 1
            segment = Segment(self._frames[:keep], SegmentReason.IDLE)
            self._pre_roll.extend(self._frames[-PRE_ROLL_FRAMES:])
            self._clear_segment()
            self._state = _State.IDLE
            return [segment]

        valley = self._find_valley()
        if valley is not None:
            segment = Segment(self._frames[: valley + 1], SegmentReason.COARTICULATION)
            self._frames = self._frames[valley + 1:]
            self._motion = self._motion[valley + 1:]
            self._idle_run = 0
            return [segment]

        if len(self._frames) >= SEGMENT_MAX_FRAMES:
            segment = Segment(self._frames, SegmentReason.MAX_LENGTH)
            self._clear_segment()
            self._state = _State.IDLE
            return [segment]

        return []

    def _find_valley(self) -> Optional[int]:
        """Index of a deep motion minimum between two signs, or None.

        The motion curve is smoothed with a centered 3-point average. A valley
        is accepted when it is a local minimum, falls below
        COARTICULATION_DIP_RATIO of the segment's peak, enough frames precede it,
        and raw motion is back above MOTION_THRESHOLD (the next sign has begun).
        """
        m = self._motion
        n = len(m)
        i = n - 3
        if i < 2 or i + 1 < COARTICULATION_MIN_SEGMENT_FRAMES:
            return None

        def s(k: int) -> float:
            return (m[k - 1] + m[k] + m[k + 1]) / 3

        a, b, c = s(i - 1), s(i), s(i + 1)
        if not (b <= a and b < c):
            return None
        peak = max(s(k) for k in range(1, i))
        if b > peak * COARTICULATION_DIP_RATIO:
            return None
        # Motion must have risen again: the next sign has begun.
        if max(m[i + 1], m[i + 2]) < MOTION_THRESHOLD:
            return None
        return i

    def flush(self) -> Optional[Segment]:
        """Close the current segment on request (for example on 'finalize')."""
        if self._state is not _State.ACTIVE or not self._frames:
            self._cand_frames, self._cand_motion = [], []
            return None
        segment = Segment(self._frames, SegmentReason.FLUSH)
        self._clear_segment()
        self._state = _State.IDLE
        return segment

    def _clear_segment(self) -> None:
        self._frames, self._motion = [], []
        self._cand_frames, self._cand_motion = [], []
        self._idle_run = 0
