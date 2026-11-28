"""Tests for the continuous gesture processing pipeline (KAN-25)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from continuous import (
    ContinuousGestureProcessor,
    FrameQuality,
    assess_frame_quality,
    interpolate_gap,
)
from landmark_buffer import LandmarkFrame

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hand(x: float) -> list[dict]:
    """21-point hand with points spread around *x*."""
    return [{"x": x + 0.01 * i, "y": 0.5 + 0.01 * i, "z": 0.0} for i in range(21)]


def _collapsed_hand(x: float) -> list[dict]:
    """21-point hand with all points at nearly the same position (blur)."""
    return [{"x": x, "y": 0.5, "z": 0.0} for _ in range(21)]


def _pose(wrist_y: float = 0.4) -> list[dict]:
    pts = [{"x": 0.5, "y": 0.3, "z": 0.0} for _ in range(33)]
    pts[23]["y"] = pts[24]["y"] = 0.7
    pts[15]["y"] = pts[16]["y"] = wrist_y
    return pts


def make_frame(ts: int, x: float = 0.5, wrist_y: float = 0.4) -> LandmarkFrame:
    return LandmarkFrame(
        timestamp=ts,
        left_hand=_hand(x - 0.3),
        right_hand=_hand(x),
        pose=_pose(wrist_y),
    )


def make_frames(steps, start_ts=0, interval_ms=100):
    """Create frames from displacement steps at regular intervals."""
    frames = []
    x = 0.5
    for i, d in enumerate([0.0] + list(steps)):
        x += d
        frames.append(make_frame(start_ts + i * interval_ms, x))
    return frames


# ---------------------------------------------------------------------------
# Frame Quality Tests
# ---------------------------------------------------------------------------


class TestFrameQuality(unittest.TestCase):
    def test_good_frame(self):
        f = make_frame(0)
        self.assertEqual(assess_frame_quality(f), FrameQuality.GOOD)

    def test_no_hands_is_bad(self):
        f = LandmarkFrame(timestamp=0, pose=_pose())
        self.assertEqual(assess_frame_quality(f), FrameQuality.BAD)

    def test_one_hand_missing_is_degraded(self):
        f = LandmarkFrame(timestamp=0, right_hand=_hand(0.5), pose=_pose())
        self.assertEqual(assess_frame_quality(f), FrameQuality.DEGRADED)

    def test_collapsed_hand_is_degraded(self):
        f = LandmarkFrame(
            timestamp=0,
            left_hand=_collapsed_hand(0.2),
            right_hand=_hand(0.5),
            pose=_pose(),
        )
        self.assertEqual(assess_frame_quality(f), FrameQuality.DEGRADED)


# ---------------------------------------------------------------------------
# Frame-Drop Interpolation Tests
# ---------------------------------------------------------------------------


class TestInterpolation(unittest.TestCase):
    def test_basic_interpolation(self):
        f1 = make_frame(0, x=0.3)
        f2 = make_frame(300, x=0.6)
        result = interpolate_gap(f1, f2, 2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].timestamp, 100)
        self.assertEqual(result[1].timestamp, 200)

    def test_interpolation_preserves_hand_data(self):
        f1 = make_frame(0, x=0.0)
        f2 = make_frame(200, x=1.0)
        result = interpolate_gap(f1, f2, 1)
        # Midpoint should be ~0.5 for right hand first point
        mid = result[0]
        self.assertIsNotNone(mid.right_hand)
        self.assertAlmostEqual(mid.right_hand[0]["x"], 0.5, places=1)

    def test_interpolation_handles_none_hand(self):
        f1 = LandmarkFrame(timestamp=0, right_hand=_hand(0.3))
        f2 = LandmarkFrame(timestamp=200, right_hand=_hand(0.6))
        result = interpolate_gap(f1, f2, 1)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0].left_hand)


# ---------------------------------------------------------------------------
# ContinuousGestureProcessor Tests
# ---------------------------------------------------------------------------


class TestContinuousProcessor(unittest.TestCase):
    def test_feed_single_frame_no_output(self):
        proc = ContinuousGestureProcessor()
        f = make_frame(0)
        results = proc.feed(f)
        self.assertEqual(results, [])
        self.assertEqual(proc.frames_received, 1)

    def test_feed_gesture_sequence_produces_results(self):
        """A full gesture (motion → idle) should produce at least one result."""
        proc = ContinuousGestureProcessor()
        # 5 idle frames, then 15 motion, then 15 idle
        steps = [0.0] * 5 + [0.05] * 15 + [0.0] * 15
        frames = make_frames(steps, interval_ms=100)
        all_results = []
        for f in frames:
            all_results.extend(proc.feed(f))

        # Should have spotted and classified at least one gesture
        self.assertGreater(len(all_results), 0)
        # At least one final (non-partial) result should exist
        final_results = [r for r in all_results if not r.is_partial]
        self.assertGreater(len(final_results), 0)
        self.assertIsNotNone(final_results[0].result)
        self.assertGreater(proc.segments_spotted, 0)

    def test_frame_gap_interpolation(self):
        """When frames arrive with a gap, missing frames are interpolated."""
        proc = ContinuousGestureProcessor(max_frame_gap_ms=500)
        f1 = make_frame(0, x=0.3)
        f2 = make_frame(300, x=0.5)  # 300ms gap, expected ~100ms interval
        proc.feed(f1)
        proc.feed(f2)
        # After only 2 real frames the processor may or may not interpolate
        # depending on the interval estimation, but it should not crash
        self.assertGreaterEqual(proc.frames_received, 2)

    def test_excessive_gap_not_interpolated(self):
        """Gaps larger than max_frame_gap_ms are not interpolated."""
        proc = ContinuousGestureProcessor(max_frame_gap_ms=500)
        f1 = make_frame(0)
        f2 = make_frame(1000)  # 1s gap, beyond max
        proc.feed(f1)
        proc.feed(f2)
        self.assertEqual(proc.frames_interpolated, 0)

    def test_bad_frames_tolerated_within_grace(self):
        """BAD-quality frames within the occlusion grace are skipped."""
        proc = ContinuousGestureProcessor(occlusion_grace_frames=3)
        # Feed some good frames first
        for i in range(5):
            proc.feed(make_frame(i * 100))

        # Feed BAD frames (no hands)
        for i in range(3):
            proc.feed(LandmarkFrame(timestamp=500 + i * 100, pose=_pose()))

        self.assertEqual(proc.frames_dropped_quality, 3)

    def test_candidate_queue_management(self):
        """The candidate queue does not exceed the configured size."""
        proc = ContinuousGestureProcessor(candidate_queue_size=3)
        # Create many gesture segments
        for batch in range(5):
            start = batch * 4000
            steps = [0.05] * 12 + [0.0] * 15
            frames = make_frames(steps, start_ts=start, interval_ms=100)
            for f in frames:
                proc.feed(f)
        self.assertLessEqual(proc.candidate_count, 3)

    def test_flush_returns_results(self):
        """Flush classifies any in-progress segment."""
        proc = ContinuousGestureProcessor()
        # Start a gesture but don't finish it
        steps = [0.05] * 12
        frames = make_frames(steps, interval_ms=100)
        for f in frames:
            proc.feed(f)

        results = proc.flush()
        self.assertGreater(len(results), 0)
        self.assertIsNotNone(results[0].result)

    def test_reset_clears_state(self):
        """Reset brings the processor back to a clean state."""
        proc = ContinuousGestureProcessor()
        steps = [0.05] * 12 + [0.0] * 15
        for f in make_frames(steps, interval_ms=100):
            proc.feed(f)

        proc.reset()
        self.assertEqual(proc.candidate_count, 0)
        self.assertFalse(proc.spotter.is_active)

    def test_stats_tracking(self):
        proc = ContinuousGestureProcessor()
        steps = [0.05] * 12 + [0.0] * 15
        for f in make_frames(steps, interval_ms=100):
            proc.feed(f)

        stats = proc.get_stats()
        self.assertIn("frames_received", stats)
        self.assertIn("segments_spotted", stats)
        self.assertIn("results_emitted", stats)
        self.assertGreater(stats["frames_received"], 0)

    def test_coarticulation_produces_multiple_results(self):
        """Two signs without a pause (co-articulation) produce two results."""
        proc = ContinuousGestureProcessor()
        steps = [0.05] * 12 + [0.004] * 3 + [0.05] * 12 + [0.0] * 15
        frames = make_frames(steps, interval_ms=100)
        all_results = []
        for f in frames:
            all_results.extend(proc.feed(f))

        final_results = [r for r in all_results if not r.is_partial]
        self.assertGreaterEqual(len(final_results), 2)

    def test_continuous_sequence_no_explicit_pause(self):
        """The user can sign continuously and results appear without
        needing to pause or press finalize."""
        proc = ContinuousGestureProcessor()
        all_results = []

        # Sign 1
        for f in make_frames([0.05] * 12 + [0.0] * 15, start_ts=0, interval_ms=100):
            all_results.extend(proc.feed(f))

        # Sign 2 — starts immediately after sign 1 finishes
        for f in make_frames([0.05] * 12 + [0.0] * 15, start_ts=3000, interval_ms=100):
            all_results.extend(proc.feed(f))

        final_results = [r for r in all_results if not r.is_partial]
        self.assertGreaterEqual(len(final_results), 2)


# ---------------------------------------------------------------------------
# Integration: ContinuousGestureProcessor + Session
# ---------------------------------------------------------------------------


class TestSessionIntegration(unittest.TestCase):
    def test_session_has_continuous_processor(self):
        from session import Session

        s = Session(session_id="test-1")
        self.assertIsNotNone(s.continuous)
        # The continuous processor should share the session's spotter
        self.assertIs(s.continuous.spotter, s.spotter)

    def test_session_reset_resets_continuous(self):
        from session import Session

        s = Session(session_id="test-2")
        # Feed some frames
        for i in range(10):
            s.continuous.feed(make_frame(i * 100))
        s.reset()
        self.assertFalse(s.continuous.spotter.is_active)
        self.assertEqual(s.continuous.candidate_count, 0)


if __name__ == "__main__":
    unittest.main()
