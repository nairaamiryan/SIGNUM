"""Tests for Gesture Lifecycle Management (KAN-26)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from landmark_buffer import LandmarkFrame
from lifecycle import (
    GestureLifecycleManager,
    LifecycleConfig,
    LifecyclePhase,
    assess_signer_positioning,
)
from session import Session


def _hand(x: float = 0.5, y: float = 0.5) -> list[dict]:
    return [{"x": x + 0.01 * i, "y": y + 0.01 * i, "z": 0.0} for i in range(21)]


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


def _frame(
    ts: int,
    *,
    positioned: bool = True,
    neutral: bool = False,
    present: bool = True,
) -> LandmarkFrame:
    if not present:
        return LandmarkFrame(timestamp=ts)
    if not positioned:
        # Shoulders outside active margin (0.08)
        return LandmarkFrame(
            timestamp=ts,
            right_hand=_hand(0.02, 0.5),
            pose=_pose(left_sh_x=0.01, right_sh_x=0.05, wrist_y=0.9 if neutral else 0.4),
        )
    return LandmarkFrame(
        timestamp=ts,
        left_hand=_hand(0.3, 0.5),
        right_hand=_hand(0.6, 0.5),
        pose=_pose(wrist_y=0.9 if neutral else 0.4),
    )


class TestSignerPositioning(unittest.TestCase):
    def test_absent_signer(self):
        present, positioned = assess_signer_positioning(_frame(0, present=False))
        self.assertFalse(present)
        self.assertFalse(positioned)

    def test_out_of_active_area(self):
        present, positioned = assess_signer_positioning(_frame(0, positioned=False))
        self.assertTrue(present)
        self.assertFalse(positioned)

    def test_centered_signer_is_positioned(self):
        present, positioned = assess_signer_positioning(_frame(0, positioned=True))
        self.assertTrue(present)
        self.assertTrue(positioned)

    def test_hand_only_fallback_positioning(self):
        f = LandmarkFrame(timestamp=0, right_hand=_hand(0.5, 0.5))
        present, positioned = assess_signer_positioning(f)
        self.assertTrue(present)
        self.assertTrue(positioned)


class TestLifecycleManager(unittest.TestCase):
    def _cfg(self, **kwargs) -> LifecycleConfig:
        defaults = dict(
            active_area_margin=0.08,
            min_shoulder_span=0.08,
            start_hold_ms=200,
            inactivity_ms=1000,
            finalize_timeout_ms=2000,
            neutral_end_frames=3,
        )
        defaults.update(kwargs)
        return LifecycleConfig(**defaults)

    def test_start_detection_requires_active_area_and_hold(self):
        mgr = GestureLifecycleManager(self._cfg(start_hold_ms=200))
        self.assertEqual(mgr.phase, LifecyclePhase.IDLE)

        # Positioned at t=0 -> still IDLE until hold completes
        u0 = mgr.on_frame(_frame(0), spotter_active=False, has_pending_glosses=False)
        self.assertEqual(u0.phase, LifecyclePhase.IDLE)

        # Held for 200ms -> READY
        u1 = mgr.on_frame(_frame(200), spotter_active=False, has_pending_glosses=False)
        self.assertEqual(u1.phase, LifecyclePhase.READY)
        self.assertTrue(u1.changed)

    def test_active_signing_and_inactivity_to_auto_finalize(self):
        mgr = GestureLifecycleManager(self._cfg())
        mgr.on_frame(_frame(0), spotter_active=False, has_pending_glosses=False)
        mgr.on_frame(_frame(200), spotter_active=False, has_pending_glosses=False)

        # Active signing begins
        u_sign = mgr.on_frame(_frame(300), spotter_active=True, has_pending_glosses=False)
        self.assertEqual(u_sign.phase, LifecyclePhase.SIGNING)
        self.assertTrue(u_sign.changed)

        # Motion stops -> inactivity period reached at 1300ms (1000ms elapsed)
        u_inact = mgr.on_frame(_frame(1300), spotter_active=False, has_pending_glosses=True)
        self.assertEqual(u_inact.phase, LifecyclePhase.INACTIVE)
        self.assertGreaterEqual(u_inact.inactivity_ms, 1000)
        self.assertFalse(u_inact.should_finalize)

        # Finalize timeout reached at 2300ms (2000ms elapsed) -> FINALIZING
        u_fin = mgr.on_frame(_frame(2300), spotter_active=False, has_pending_glosses=True)
        self.assertEqual(u_fin.phase, LifecyclePhase.FINALIZING)
        self.assertTrue(u_fin.should_finalize)

        # After finalization completes -> READY
        u_done = mgr.on_finalized()
        self.assertEqual(u_done.phase, LifecyclePhase.READY)

    def test_neutral_posture_ends_signing_and_triggers_finalize(self):
        mgr = GestureLifecycleManager(self._cfg(neutral_end_frames=3))
        mgr.on_frame(_frame(0), spotter_active=True, has_pending_glosses=True)
        self.assertEqual(mgr.phase, LifecyclePhase.SIGNING)

        # 2 neutral frames -> not yet ended
        mgr.on_frame(_frame(100, neutral=True), spotter_active=False, has_pending_glosses=True)
        mgr.on_frame(_frame(200, neutral=True), spotter_active=False, has_pending_glosses=True)
        self.assertEqual(mgr.phase, LifecyclePhase.SIGNING)

        # 3rd neutral frame -> triggers finalization
        u = mgr.on_frame(_frame(300, neutral=True), spotter_active=False, has_pending_glosses=True)
        self.assertEqual(u.phase, LifecyclePhase.FINALIZING)
        self.assertEqual(u.reason, "neutral_posture")
        self.assertTrue(u.should_finalize)

    def test_manual_finalize_and_manual_termination(self):
        mgr = GestureLifecycleManager(self._cfg())
        mgr.on_frame(_frame(0), spotter_active=True, has_pending_glosses=True)

        u_man_fin = mgr.on_manual_finalize()
        self.assertEqual(u_man_fin.phase, LifecyclePhase.FINALIZING)
        self.assertEqual(u_man_fin.reason, "manual_finalize")
        self.assertTrue(u_man_fin.should_finalize)

        u_done = mgr.on_finalized()
        self.assertEqual(u_done.phase, LifecyclePhase.READY)

        u_term = mgr.on_manual_terminate()
        self.assertEqual(u_term.phase, LifecyclePhase.TERMINATED)
        self.assertEqual(u_term.reason, "manual_termination")
        self.assertFalse(u_term.should_finalize)

    def test_message_serialization_and_session_integration(self):
        s = Session(session_id="s-lifecycle")
        u = s.lifecycle.on_frame(_frame(0), spotter_active=True, has_pending_glosses=False)
        msg = u.to_message(s.session_id)
        self.assertEqual(msg["type"], "lifecycle")
        self.assertEqual(msg["sessionId"], "s-lifecycle")
        self.assertEqual(msg["phase"], "signing")
        self.assertTrue(msg["signerPresent"])
        self.assertTrue(msg["signerPositioned"])

        s.reset()
        self.assertEqual(s.lifecycle.phase, LifecyclePhase.IDLE)

    def test_config_from_env(self):
        os.environ["LIFECYCLE_INACTIVITY_MS"] = "1500"
        os.environ["LIFECYCLE_FINALIZE_TIMEOUT_MS"] = "3000"
        try:
            cfg = LifecycleConfig.from_env()
            self.assertEqual(cfg.inactivity_ms, 1500)
            self.assertEqual(cfg.finalize_timeout_ms, 3000)
        finally:
            os.environ.pop("LIFECYCLE_INACTIVITY_MS", None)
            os.environ.pop("LIFECYCLE_FINALIZE_TIMEOUT_MS", None)


if __name__ == "__main__":
    unittest.main()
