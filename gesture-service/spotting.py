"""
Gesture spotting (segmentation).

Scans the buffered landmark frames to determine whether the signer is
currently mid-gesture ("active") or at rest ("idle"), using a simple
motion-intensity heuristic over hand landmark displacement between
consecutive frames.

This is a first-pass heuristic, not a learned model — it exists to filter
out idle/noise frames before they reach classification, per the sliding
window approach described in technical.md.
"""

from landmark_buffer import LandmarkFrame
from constants import MOTION_THRESHOLD, MIN_ACTIVE_FRAMES, IDLE_FRAMES_TO_END_SEGMENT


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
    """Determines whether the most recent frames in the buffer represent
    an active gesture segment, based on sustained motion above threshold.

    Returns True once at least MIN_ACTIVE_FRAMES consecutive frames show
    motion above MOTION_THRESHOLD among the most recent frames.
    """
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
    """Determines whether the signer has returned to rest, based on
    sustained low motion over the most recent frames — used to decide
    when an active gesture segment has ended."""
    if len(frames) < IDLE_FRAMES_TO_END_SEGMENT + 1:
        return False

    for i in range(len(frames) - 1, len(frames) - 1 - IDLE_FRAMES_TO_END_SEGMENT, -1):
        intensity = frame_motion_intensity(frames[i - 1], frames[i])
        if intensity >= MOTION_THRESHOLD:
            return False

    return True