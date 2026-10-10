"""
Sliding-window buffer for per-session landmark frames.

Each WebSocket session accumulates incoming landmark frames here. The
buffer keeps only the most recent BUFFER_MAX_FRAMES frames, which the
gesture spotting step (spotting.py) scans to detect active gesture
segments.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from constants import BUFFER_MAX_FRAMES


@dataclass
class LandmarkFrame:
    """A single frame of landmark data, mirroring the frontend's
    ClientLandmarksMessage payload (see docs/websocket-contract.md)."""

    timestamp: int
    left_hand: Optional[list[dict]] = None
    right_hand: Optional[list[dict]] = None
    face: Optional[list[dict]] = None
    pose: Optional[list[dict]] = None


class LandmarkBuffer:
    """Fixed-size sliding window of the most recent landmark frames for
    one recognition session."""

    def __init__(self, max_frames: int = BUFFER_MAX_FRAMES):
        self._frames: deque[LandmarkFrame] = deque(maxlen=max_frames)

    def add(self, frame: LandmarkFrame) -> None:
        self._frames.append(frame)

    def frames(self) -> list[LandmarkFrame]:
        """Returns the buffered frames, oldest first."""
        return list(self._frames)

    def clear(self) -> None:
        self._frames.clear()

    def __len__(self) -> int:
        return len(self._frames)

    @property
    def is_empty(self) -> bool:
        return len(self._frames) == 0