"""
Per-connection session state for the Gesture Recognition Service.

Each WebSocket connection gets one Session instance, tracking its
recognition state, landmark buffer, and last-activity time (used for
idle-session cleanup).
"""

import time
from dataclasses import dataclass, field
from enum import Enum

from landmark_buffer import LandmarkBuffer


class RecognitionState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class Session:
    session_id: str
    state: RecognitionState = RecognitionState.IDLE
    buffer: LandmarkBuffer = field(default_factory=LandmarkBuffer)
    last_activity: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        """Marks the session as recently active."""
        self.last_activity = time.monotonic()

    def is_stale(self, timeout_seconds: float) -> bool:
        return (time.monotonic() - self.last_activity) > timeout_seconds

    def reset(self) -> None:
        """Clears the buffer and returns to listening state after a
        finalize/classification cycle completes."""
        self.buffer.clear()
        self.state = RecognitionState.LISTENING


class SessionRegistry:
    """Keeps track of active sessions by session_id. In this single-process
    mock service, sessions live in memory; a production deployment with
    multiple workers would back this with shared storage (e.g. Redis)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)