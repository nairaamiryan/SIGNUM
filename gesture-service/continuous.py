"""
Continuous Gesture Processing pipeline (KAN-25).

Provides the ``ContinuousGestureProcessor`` that wraps the existing
spotting and classification layers into a streaming pipeline that:

  * feeds every incoming frame through sliding-window analysis,
  * manages a **temporal buffer** wider than the spotter's internal
    state so that frame-drop recovery and re-classification are possible,
  * maintains a **candidate gesture queue** so the caller (WebSocket
    handler) can emit partial results as soon as they appear,
  * performs **continuous gesture segmentation** (no explicit pause
    required between signs),
  * handles **co-articulation and transitions** (via the spotter's
    valley-based split),
  * tolerates **short frame drops** (gap interpolation),
  * tolerates **brief occlusion and motion blur** (quality scoring),
  * streams classification results with **low latency**.

Thread-safety: one instance per session, used only from one asyncio
task (the WebSocket handler). No locks needed.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from classification import ClassificationResult, classify_segment
from constants import (
    CONTINUOUS_CANDIDATE_QUEUE_SIZE,
    CONTINUOUS_MAX_FRAME_GAP_MS,
    CONTINUOUS_MIN_CANDIDATE_CONFIDENCE,
    CONTINUOUS_OCCLUSION_GRACE_FRAMES,
    CONTINUOUS_PARTIAL_EMIT_INTERVAL_MS,
    CONTINUOUS_QUALITY_BLUR_THRESHOLD,
    CONTINUOUS_RECLASS_COOLDOWN_MS,
    CONTINUOUS_TEMPORAL_BUFFER_SECONDS,
)
from landmark_buffer import LandmarkFrame
from spotting import HeuristicGestureSpotter, Segment

logger = logging.getLogger("gesture-service.continuous")


# ---------------------------------------------------------------------------
# Frame quality assessment
# ---------------------------------------------------------------------------


class FrameQuality(str, Enum):
    """Quality classification of a single landmark frame."""

    GOOD = "good"
    DEGRADED = "degraded"  # partial occlusion or motion blur
    BAD = "bad"  # fully occluded or missing data


def assess_frame_quality(frame: LandmarkFrame) -> FrameQuality:
    """Score a frame for occlusion and motion-blur artefacts.

    Rules:
      * Both hands None → BAD
      * One hand None → DEGRADED
      * Any hand with very low per-point variance (all points collapsed
        to nearly the same position, a sign of tracking loss) → DEGRADED
    """
    has_left = frame.left_hand is not None and len(frame.left_hand) > 0
    has_right = frame.right_hand is not None and len(frame.right_hand) > 0

    if not has_left and not has_right:
        return FrameQuality.BAD

    if not has_left or not has_right:
        return FrameQuality.DEGRADED

    # Check for collapsed tracking (motion-blur artefact)
    for hand in (frame.left_hand, frame.right_hand):
        if hand and len(hand) >= 2:
            xs = [p["x"] for p in hand]
            ys = [p["y"] for p in hand]
            spread = max(xs) - min(xs) + max(ys) - min(ys)
            if spread < CONTINUOUS_QUALITY_BLUR_THRESHOLD:
                return FrameQuality.DEGRADED

    return FrameQuality.GOOD


# ---------------------------------------------------------------------------
# Frame-drop interpolation
# ---------------------------------------------------------------------------


def _lerp_point(a: dict, b: dict, t: float) -> dict:
    return {
        "x": a["x"] + (b["x"] - a["x"]) * t,
        "y": a["y"] + (b["y"] - a["y"]) * t,
        "z": a.get("z", 0.0) + (b.get("z", 0.0) - a.get("z", 0.0)) * t,
    }


def _lerp_landmarks(
    a: list[dict] | None,
    b: list[dict] | None,
    t: float,
) -> list[dict] | None:
    if a is None or b is None:
        return a or b
    if len(a) != len(b):
        return b
    return [_lerp_point(ap, bp, t) for ap, bp in zip(a, b)]


def interpolate_gap(
    prev: LandmarkFrame,
    curr: LandmarkFrame,
    n_missing: int,
) -> list[LandmarkFrame]:
    """Generate *n_missing* evenly-spaced synthetic frames between *prev*
    and *curr* by linear interpolation. The interpolated frames receive
    timestamps that fill the gap uniformly."""
    result: list[LandmarkFrame] = []
    for i in range(1, n_missing + 1):
        t = i / (n_missing + 1)
        ts = int(prev.timestamp + (curr.timestamp - prev.timestamp) * t)
        result.append(
            LandmarkFrame(
                timestamp=ts,
                left_hand=_lerp_landmarks(prev.left_hand, curr.left_hand, t),
                right_hand=_lerp_landmarks(prev.right_hand, curr.right_hand, t),
                face=_lerp_landmarks(prev.face, curr.face, t),
                pose=_lerp_landmarks(prev.pose, curr.pose, t),
            )
        )
    return result


# ---------------------------------------------------------------------------
# Candidate gesture in the queue
# ---------------------------------------------------------------------------


class CandidateStatus(str, Enum):
    PENDING = "pending"  # segment spotted, not yet classified
    CLASSIFIED = "classified"  # classification result available
    EMITTED = "emitted"  # sent to the client
    DROPPED = "dropped"  # too low confidence, will not be sent


@dataclass
class CandidateGesture:
    """One candidate gesture in the streaming queue."""

    segment: Segment
    status: CandidateStatus = CandidateStatus.PENDING
    result: Optional[ClassificationResult] = None
    created_at: float = field(default_factory=time.monotonic)
    classified_at: Optional[float] = None
    quality_scores: list[FrameQuality] = field(default_factory=list)

    @property
    def avg_quality_good_ratio(self) -> float:
        if not self.quality_scores:
            return 1.0
        good = sum(1 for q in self.quality_scores if q == FrameQuality.GOOD)
        return good / len(self.quality_scores)


# ---------------------------------------------------------------------------
# Streaming results
# ---------------------------------------------------------------------------


@dataclass
class StreamingResult:
    """A recognition result ready to be sent over the WebSocket."""

    candidate: CandidateGesture
    result: ClassificationResult
    is_partial: bool  # True = intermediate update; False = final for this segment
    latency_ms: float  # processing latency from segment end to result


# ---------------------------------------------------------------------------
# ContinuousGestureProcessor
# ---------------------------------------------------------------------------


class ContinuousGestureProcessor:
    """Continuous gesture processing pipeline for one session.

    Usage (in the WebSocket handler)::

        processor = ContinuousGestureProcessor()
        for frame in incoming_frames:
            for streaming_result in processor.feed(frame):
                await websocket.send(streaming_result)
    """

    def __init__(
        self,
        spotter: HeuristicGestureSpotter | None = None,
        *,
        temporal_buffer_seconds: float = CONTINUOUS_TEMPORAL_BUFFER_SECONDS,
        max_frame_gap_ms: int = CONTINUOUS_MAX_FRAME_GAP_MS,
        candidate_queue_size: int = CONTINUOUS_CANDIDATE_QUEUE_SIZE,
        min_candidate_confidence: float = CONTINUOUS_MIN_CANDIDATE_CONFIDENCE,
        occlusion_grace_frames: int = CONTINUOUS_OCCLUSION_GRACE_FRAMES,
        partial_emit_interval_ms: int = CONTINUOUS_PARTIAL_EMIT_INTERVAL_MS,
        reclass_cooldown_ms: int = CONTINUOUS_RECLASS_COOLDOWN_MS,
    ) -> None:
        self._spotter = spotter or HeuristicGestureSpotter()

        # --- temporal buffer (wider than the spotter's own frame list) ---
        self._temporal_buffer_ms = int(temporal_buffer_seconds * 1000)
        self._temporal_buffer: deque[LandmarkFrame] = deque()

        # --- frame-drop interpolation ---
        self._max_frame_gap_ms = max_frame_gap_ms
        self._expected_interval_ms: float = 100.0  # ~10 fps; auto-tuned
        self._last_frame: LandmarkFrame | None = None
        self._frame_intervals: deque[float] = deque(maxlen=20)

        # --- candidate gesture queue ---
        self._queue_size = candidate_queue_size
        self._candidates: deque[CandidateGesture] = deque(maxlen=candidate_queue_size)

        # --- quality / occlusion ---
        self._min_candidate_confidence = min_candidate_confidence
        self._occlusion_grace = occlusion_grace_frames
        self._bad_frame_run = 0

        # --- streaming ---
        self._partial_interval_ms = partial_emit_interval_ms
        self._reclass_cooldown_ms = reclass_cooldown_ms
        self._last_partial_emit_ms: int = 0

        # --- stats ---
        self.frames_received: int = 0
        self.frames_interpolated: int = 0
        self.frames_dropped_quality: int = 0
        self.segments_spotted: int = 0
        self.results_emitted: int = 0

    # ------------------------------------------------------------------ public

    @property
    def spotter(self) -> HeuristicGestureSpotter:
        return self._spotter

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    @property
    def pending_candidates(self) -> list[CandidateGesture]:
        return [c for c in self._candidates if c.status == CandidateStatus.PENDING]

    def feed(self, frame: LandmarkFrame) -> list[StreamingResult]:
        """Feed one landmark frame and return any results ready to stream.

        This is the **single entry point** called by the WebSocket handler
        for every ``landmarks`` message. It performs all pipeline stages:

        1. Frame-drop detection and interpolation
        2. Quality assessment (occlusion / blur tolerance)
        3. Temporal buffer update
        4. Gesture spotting (segmentation)
        5. Classification of completed segments
        6. Candidate queue management
        7. Streaming result assembly
        """
        results: list[StreamingResult] = []

        # 1. Frame-drop detection → interpolate missing frames
        frames_to_process = self._handle_frame_gaps(frame)

        for f in frames_to_process:
            self.frames_received += 1

            # 2. Quality assessment
            quality = assess_frame_quality(f)
            if quality == FrameQuality.BAD:
                self._bad_frame_run += 1
                self.frames_dropped_quality += 1
                if self._bad_frame_run <= self._occlusion_grace:
                    # Tolerate a short run of bad frames
                    continue
                # Beyond grace period: still feed to spotter so it can
                # detect the idle→close transition.

            else:
                self._bad_frame_run = 0

            # 3. Temporal buffer update
            self._add_to_temporal_buffer(f)

            # 4. Gesture spotting
            segments = self._spotter.process(f)
            for seg in segments:
                self.segments_spotted += 1
                quality_scores = [assess_frame_quality(sf) for sf in seg.frames]
                candidate = CandidateGesture(
                    segment=seg,
                    quality_scores=quality_scores,
                )
                self._enqueue_candidate(candidate)

                # 5. Classify immediately (low-latency)
                seg_results = self._classify_candidate(candidate)
                results.extend(seg_results)

        # 6. Check if we should emit a partial update for in-progress segments
        if self._spotter.is_active and self._should_emit_partial(frame.timestamp):
            partial = self._emit_partial_for_active()
            if partial is not None:
                results.append(partial)

        return results

    def flush(self) -> list[StreamingResult]:
        """Flush the spotter (e.g. on ``finalize``) and classify any remaining
        segment. Returns results for the flushed segment."""
        results: list[StreamingResult] = []
        segment = self._spotter.flush()
        if segment is not None:
            self.segments_spotted += 1
            quality_scores = [assess_frame_quality(f) for f in segment.frames]
            candidate = CandidateGesture(
                segment=segment,
                quality_scores=quality_scores,
            )
            self._enqueue_candidate(candidate)
            results.extend(self._classify_candidate(candidate))
        return results

    def reset(self) -> None:
        """Reset the entire pipeline (e.g. on ``restart``)."""
        self._spotter.reset()
        self._temporal_buffer.clear()
        self._candidates.clear()
        self._last_frame = None
        self._bad_frame_run = 0
        self._last_partial_emit_ms = 0

    def get_stats(self) -> dict[str, Any]:
        return {
            "frames_received": self.frames_received,
            "frames_interpolated": self.frames_interpolated,
            "frames_dropped_quality": self.frames_dropped_quality,
            "segments_spotted": self.segments_spotted,
            "results_emitted": self.results_emitted,
            "candidate_queue_length": len(self._candidates),
            "temporal_buffer_length": len(self._temporal_buffer),
        }

    # ---------------------------------------------------------------- internal

    def _handle_frame_gaps(self, frame: LandmarkFrame) -> list[LandmarkFrame]:
        """Detect gaps between frames and interpolate missing ones."""
        if self._last_frame is None:
            self._last_frame = frame
            return [frame]

        gap_ms = frame.timestamp - self._last_frame.timestamp
        self._frame_intervals.append(gap_ms)

        # Auto-tune expected interval
        if len(self._frame_intervals) >= 5:
            sorted_intervals = sorted(self._frame_intervals)
            self._expected_interval_ms = sorted_intervals[len(sorted_intervals) // 2]

        result: list[LandmarkFrame] = []

        if gap_ms > self._max_frame_gap_ms:
            # Too large a gap — don't interpolate, just accept discontinuity
            logger.debug(
                "Frame gap %d ms exceeds max %d ms, skipping interpolation",
                gap_ms,
                self._max_frame_gap_ms,
            )
        elif self._expected_interval_ms > 0 and gap_ms > self._expected_interval_ms * 1.8:
            # Short gap — interpolate
            n_missing = max(1, round(gap_ms / self._expected_interval_ms) - 1)
            n_missing = min(n_missing, 5)  # cap interpolation
            interpolated = interpolate_gap(self._last_frame, frame, n_missing)
            result.extend(interpolated)
            self.frames_interpolated += len(interpolated)
            logger.debug(
                "Interpolated %d frames for %d ms gap",
                len(interpolated),
                gap_ms,
            )

        result.append(frame)
        self._last_frame = frame
        return result

    def _add_to_temporal_buffer(self, frame: LandmarkFrame) -> None:
        """Add frame to the temporal buffer, pruning old frames."""
        self._temporal_buffer.append(frame)
        cutoff = frame.timestamp - self._temporal_buffer_ms
        while self._temporal_buffer and self._temporal_buffer[0].timestamp < cutoff:
            self._temporal_buffer.popleft()

    def _enqueue_candidate(self, candidate: CandidateGesture) -> None:
        """Add a candidate to the queue, evicting the oldest if full."""
        if len(self._candidates) >= self._queue_size:
            oldest = self._candidates[0]
            if oldest.status in (CandidateStatus.EMITTED, CandidateStatus.DROPPED):
                self._candidates.popleft()
            else:
                # Force-emit or drop the oldest
                oldest.status = CandidateStatus.DROPPED
                self._candidates.popleft()
        self._candidates.append(candidate)

    def _classify_candidate(
        self,
        candidate: CandidateGesture,
    ) -> list[StreamingResult]:
        """Run classification on a candidate's segment frames."""
        start = time.monotonic()

        # Filter out BAD-quality frames if enough GOOD ones remain
        good_frames = [
            f
            for f, q in zip(candidate.segment.frames, candidate.quality_scores)
            if q != FrameQuality.BAD
        ]
        frames = good_frames if len(good_frames) >= 3 else candidate.segment.frames

        result = classify_segment(frames)

        elapsed_ms = (time.monotonic() - start) * 1000
        candidate.classified_at = time.monotonic()

        if result is None or result.confidence < self._min_candidate_confidence:
            candidate.status = CandidateStatus.DROPPED
            candidate.result = result
            return []

        candidate.status = CandidateStatus.CLASSIFIED
        candidate.result = result

        latency_ms = elapsed_ms
        streaming = StreamingResult(
            candidate=candidate,
            result=result,
            is_partial=False,
            latency_ms=round(latency_ms, 2),
        )
        self.results_emitted += 1
        return [streaming]

    def _should_emit_partial(self, now_ms: int) -> bool:
        """Check if enough time has passed since the last partial emit."""
        if self._partial_interval_ms <= 0:
            return False
        return (now_ms - self._last_partial_emit_ms) >= self._partial_interval_ms

    def _emit_partial_for_active(self) -> StreamingResult | None:
        """Classify the in-progress (not yet completed) segment for a
        partial / preview result. This gives the user immediate feedback
        while they are still signing."""
        if not self._spotter.is_active:
            return None

        # Access the spotter's internal frames for a preview classification
        active_frames = list(self._spotter._frames)
        if len(active_frames) < 5:
            return None

        result = classify_segment(active_frames)
        if result is None:
            return None

        self._last_partial_emit_ms = active_frames[-1].timestamp

        # Build a temporary candidate for the partial result
        partial_candidate = CandidateGesture(
            segment=Segment(frames=active_frames, reason=None),  # type: ignore[arg-type]
            status=CandidateStatus.CLASSIFIED,
            result=result,
            quality_scores=[assess_frame_quality(f) for f in active_frames],
        )

        return StreamingResult(
            candidate=partial_candidate,
            result=result,
            is_partial=True,
            latency_ms=0.0,
        )
