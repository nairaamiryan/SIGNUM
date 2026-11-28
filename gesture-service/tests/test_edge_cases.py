"""Tests for Edge Cases and Error Recovery (KAN-27)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from constants import (
    EDGE_BLUR_STREAK_TO_WARN,
    EDGE_OCCLUSION_STREAK_TO_WARN,
    EDGE_OUT_OF_FRAME_STREAK_TO_WARN,
)
from continuous import FrameQuality
from edge_cases import (
    EdgeCaseGuard,
    EdgeWarning,
    EdgeWarningCode,
    is_hand_extraneous,
    is_non_signing_movement,
)
from landmark_buffer import LandmarkFrame
from session import Session, SessionRegistry


def _hand(x: float = 0.5, y: float = 0.5, spread: float = 0.01) -> list[dict]:
    return [{"x": x + spread * i, "y": y + spread * i, "z": 0.0} for i in range(21)]


def _pose(
    *,
    left_sh_x: float = 0.4,
    right_sh_x: float = 0.6,
    sh_y: float = 0.35,
    wrist_y: float = 0.4,
) -> list[dict]:
    pts = [{"x": 0.5, "y": 0.3, "z": 0.0} for _ in range(33)]
    pts[11] = {"x": left_sh_x, "y": sh_y, "z": 0.0}
    pts[12] = {"x": right_sh_x, "y": sh_y, "z": 0.0}
    pts[23]["y"] = pts[24]["y"] = 0.7
    pts[15]["y"] = pts[16]["y"] = wrist_y
    return pts


def _good_frame(
    ts: int,
    *,
    hand_x: float = 0.55,
    hand_y: float = 0.45,
    neutral: bool = False,
    positioned: bool = True,
) -> LandmarkFrame:
    if not positioned:
        return LandmarkFrame(
            timestamp=ts,
            right_hand=_hand(0.02, 0.5),
            pose=_pose(left_sh_x=0.01, right_sh_x=0.05, wrist_y=0.9 if neutral else 0.4),
        )
    return LandmarkFrame(
        timestamp=ts,
        left_hand=_hand(0.35, 0.45),
        right_hand=_hand(hand_x, hand_y),
        pose=_pose(wrist_y=0.9 if neutral else 0.4),
    )


class TestSpatialAndMovementHelpers(unittest.TestCase):
    def test_is_hand_extraneous(self):
        pose = _pose(left_sh_x=0.4, right_sh_x=0.6, sh_y=0.35)
        self.assertFalse(is_hand_extraneous(_hand(0.55, 0.45), pose))
        self.assertTrue(is_hand_extraneous(_hand(1.6, 0.35), pose))
        self.assertFalse(is_hand_extraneous(None, pose))
        self.assertFalse(is_hand_extraneous(_hand(1.6, 0.35), None))

    def test_is_non_signing_movement_rejects_short_neutral_and_jitter(self):
        self.assertTrue(is_non_signing_movement([_good_frame(0)]))

        neutral_frames = [_good_frame(i * 50, neutral=True) for i in range(4)]
        self.assertTrue(is_non_signing_movement(neutral_frames))

        jitter_frames = [
            _good_frame(0, hand_x=0.50, hand_y=0.45),
            _good_frame(50, hand_x=0.51, hand_y=0.45),
            _good_frame(100, hand_x=0.505, hand_y=0.455),
        ]
        self.assertTrue(is_non_signing_movement(jitter_frames))

    def test_is_non_signing_movement_accepts_real_signing(self):
        signing_frames = [
            _good_frame(0, hand_x=0.45, hand_y=0.45),
            _good_frame(50, hand_x=0.55, hand_y=0.40),
            _good_frame(100, hand_x=0.65, hand_y=0.35),
        ]
        self.assertFalse(is_non_signing_movement(signing_frames))


class TestEdgeWarningSerialization(unittest.TestCase):
    def test_to_message(self):
        warn = EdgeWarning(EdgeWarningCode.SEVERE_MOTION_BLUR, recoverable=True)
        self.assertEqual(
            warn.to_message(),
            {
                "type": "warning",
                "code": "severe_motion_blur",
                "recoverable": True,
            },
        )


class TestEdgeCaseGuard(unittest.TestCase):
    def test_poor_illumination_and_cooldown(self):
        guard = EdgeCaseGuard(cooldown_ms=1000)

        suppress, warnings = guard.inspect_frame(_good_frame(100), poor_illumination=True)
        self.assertFalse(suppress)
        self.assertEqual([w.code for w in warnings], [EdgeWarningCode.POOR_ILLUMINATION])

        # Throttled within cooldown
        _, warnings_2 = guard.inspect_frame(_good_frame(500), poor_illumination=True)
        self.assertEqual(warnings_2, [])

        # Allowed again after cooldown
        _, warnings_3 = guard.inspect_frame(_good_frame(1200), poor_illumination=True)
        self.assertEqual([w.code for w in warnings_3], [EdgeWarningCode.POOR_ILLUMINATION])

    def test_multiple_people_and_extraneous_hands_suppress_frame(self):
        guard = EdgeCaseGuard(cooldown_ms=1000)

        suppress, warnings = guard.inspect_frame(_good_frame(100), multiple_people=True)
        self.assertTrue(suppress)
        self.assertEqual([w.code for w in warnings], [EdgeWarningCode.MULTIPLE_PEOPLE])

        # Spatial extraneous hand
        far_hand_frame = LandmarkFrame(
            timestamp=200,
            right_hand=_hand(1.6, 0.35),
            pose=_pose(),
        )
        suppress_ext, warnings_ext = guard.inspect_frame(far_hand_frame)
        self.assertTrue(suppress_ext)
        self.assertEqual([w.code for w in warnings_ext], [EdgeWarningCode.EXTRANEOUS_HANDS])

    def test_severe_motion_blur_streak(self):
        guard = EdgeCaseGuard(cooldown_ms=1000)
        guard.inspect_frame(_good_frame(0, hand_x=0.20, hand_y=0.20))

        # Jump far enough to exceed EDGE_SEVERE_BLUR_MOTION_THRESHOLD (0.35)
        s1, w1 = guard.inspect_frame(_good_frame(33, hand_x=0.80, hand_y=0.80))
        self.assertTrue(s1)
        if EDGE_BLUR_STREAK_TO_WARN > 1:
            self.assertEqual(w1, [])

        s2, w2 = guard.inspect_frame(_good_frame(66, hand_x=0.10, hand_y=0.10))
        self.assertTrue(s2)
        self.assertEqual([w.code for w in w2], [EdgeWarningCode.SEVERE_MOTION_BLUR])

    def test_occlusion_streak_warns_after_threshold(self):
        guard = EdgeCaseGuard(cooldown_ms=1000)
        bad_frame = lambda ts: LandmarkFrame(timestamp=ts)  # noqa: E731

        all_warnings = []
        for i in range(EDGE_OCCLUSION_STREAK_TO_WARN):
            _, w = guard.inspect_frame(bad_frame(i * 40))
            all_warnings.extend(w)

        self.assertEqual([w.code for w in all_warnings], [EdgeWarningCode.PARTIAL_OCCLUSION])

    def test_out_of_frame_streak_warns_after_threshold(self):
        guard = EdgeCaseGuard(cooldown_ms=1000)

        all_warnings = []
        for i in range(EDGE_OUT_OF_FRAME_STREAK_TO_WARN):
            _, w = guard.inspect_frame(_good_frame(i * 40, positioned=False))
            all_warnings.extend(w)

        self.assertEqual([w.code for w in all_warnings], [EdgeWarningCode.USER_OUT_OF_FRAME])

    def test_validate_segment_rejects_bad_quality_and_non_signing(self):
        guard = EdgeCaseGuard(cooldown_ms=1000)

        ok_empty, warn_empty = guard.validate_segment([])
        self.assertFalse(ok_empty)
        self.assertIsNone(warn_empty)

        signing_frames = [
            _good_frame(0, hand_x=0.45, hand_y=0.45),
            _good_frame(50, hand_x=0.55, hand_y=0.40),
            _good_frame(100, hand_x=0.65, hand_y=0.35),
        ]
        bad_scores = [FrameQuality.BAD, FrameQuality.BAD, FrameQuality.BAD]
        ok_bad, warn_bad = guard.validate_segment(signing_frames, quality_scores=bad_scores)
        self.assertFalse(ok_bad)
        self.assertIsNotNone(warn_bad)
        self.assertEqual(warn_bad.code, EdgeWarningCode.PARTIAL_OCCLUSION)

        jitter_frames = [
            _good_frame(200, hand_x=0.50, hand_y=0.45),
            _good_frame(250, hand_x=0.505, hand_y=0.452),
        ]
        ok_jitter, warn_jitter = guard.validate_segment(jitter_frames)
        self.assertFalse(ok_jitter)
        self.assertIsNotNone(warn_jitter)
        self.assertEqual(warn_jitter.code, EdgeWarningCode.NON_SIGNING_MOVEMENT)

        ok_valid, warn_valid = guard.validate_segment(signing_frames)
        self.assertTrue(ok_valid)
        self.assertIsNone(warn_valid)


class TestSessionEdgeRecovery(unittest.TestCase):
    def test_session_has_edge_guard_and_resets_it(self):
        session = Session(session_id="s1")
        session.edge_guard.inspect_frame(_good_frame(100), poor_illumination=True)
        # Cooldown blocks immediate repeat before reset
        _, w_before = session.edge_guard.inspect_frame(_good_frame(200), poor_illumination=True)
        self.assertEqual(w_before, [])

        session.reset()
        _, w_after = session.edge_guard.inspect_frame(_good_frame(200), poor_illumination=True)
        self.assertEqual([w.code for w in w_after], [EdgeWarningCode.POOR_ILLUMINATION])

    def test_registry_cleanup_stale(self):
        registry = SessionRegistry()
        s_old = registry.get_or_create("old")
        s_fresh = registry.get_or_create("fresh")
        s_old.last_activity -= 120.0

        removed = registry.cleanup_stale(timeout_seconds=60.0)
        self.assertEqual(removed, 1)
        self.assertEqual(registry.active_count(), 1)
        self.assertIs(registry.get_or_create("fresh"), s_fresh)


if __name__ == "__main__":
    unittest.main()
