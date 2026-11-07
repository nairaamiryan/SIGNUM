import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from landmark_buffer import LandmarkFrame
from spotting import HeuristicGestureSpotter, SegmentReason, is_neutral_pose


def _hand(x: float) -> list[dict]:
    return [{"x": x, "y": 0.5, "z": 0.0} for _ in range(21)]


def _pose(wrist_y: float) -> list[dict]:
    pts = [{"x": 0.5, "y": 0.3, "z": 0.0} for _ in range(33)]
    pts[23]["y"] = pts[24]["y"] = 0.7
    pts[15]["y"] = pts[16]["y"] = wrist_y
    return pts


def make_frames(steps, wrist_y=0.4, start_ts=0):
    """steps: hand displacement per frame (equals motion intensity)."""
    frames, x = [], 0.0
    for i, d in enumerate([0.0] + list(steps)):
        x += d
        frames.append(LandmarkFrame(timestamp=start_ts + i, right_hand=_hand(x), pose=_pose(wrist_y)))
    return frames


def run(frames, spotter=None):
    spotter = spotter or HeuristicGestureSpotter()
    out = []
    for f in frames:
        out.extend(spotter.process(f))
    return spotter, out


class SpottingTests(unittest.TestCase):
    def test_single_gesture_idle_end(self):
        steps = [0.0] * 5 + [0.05] * 15 + [0.0] * 15
        _, segs = run(make_frames(steps))
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].reason, SegmentReason.IDLE)
        self.assertGreaterEqual(len(segs[0]), 15)
        self.assertLess(len(segs[0]), 15 + 3 + 5)  # tail trimmed, pre-roll small

    def test_noise_ignored(self):
        _, segs = run(make_frames([0.003] * 60))
        self.assertEqual(segs, [])

    def test_short_burst_ignored(self):
        _, segs = run(make_frames([0.05] * 3 + [0.0] * 20))
        self.assertEqual(segs, [])

    def test_coarticulation_split(self):
        steps = [0.05] * 12 + [0.004] * 3 + [0.05] * 12 + [0.0] * 15
        _, segs = run(make_frames(steps))
        reasons = [s.reason for s in segs]
        self.assertEqual(reasons, [SegmentReason.COARTICULATION, SegmentReason.IDLE])
        self.assertLess(segs[0].end_timestamp, segs[1].start_timestamp + 1)

    def test_steady_motion_not_split(self):
        steps = [0.05] * 30 + [0.0] * 15
        _, segs = run(make_frames(steps))
        self.assertEqual([s.reason for s in segs], [SegmentReason.IDLE])

    def test_neutral_pose_no_segment(self):
        frames = make_frames([0.05] * 30, wrist_y=0.9)
        self.assertTrue(is_neutral_pose(frames[0]))
        _, segs = run(frames)
        self.assertEqual(segs, [])

    def test_missing_pose_not_neutral(self):
        self.assertFalse(is_neutral_pose(LandmarkFrame(timestamp=0)))

    def test_max_length(self):
        _, segs = run(make_frames([0.05] * 100))
        self.assertTrue(segs)
        self.assertEqual(segs[0].reason, SegmentReason.MAX_LENGTH)

    def test_flush_and_reset(self):
        sp, segs = run(make_frames([0.05] * 12))
        self.assertEqual(segs, [])
        self.assertTrue(sp.is_active)
        seg = sp.flush()
        self.assertEqual(seg.reason, SegmentReason.FLUSH)
        self.assertFalse(sp.is_active)
        self.assertIsNone(sp.flush())
        run(make_frames([0.05] * 12), sp)
        sp.reset()
        self.assertFalse(sp.is_active)

    def test_pre_roll_included(self):
        steps = [0.0] * 6 + [0.05] * 12 + [0.0] * 15
        frames = make_frames(steps)
        _, segs = run(frames)
        self.assertEqual(len(segs), 1)
        first_motion_ts = 7
        self.assertLess(segs[0].start_timestamp, first_motion_ts)

    def test_two_gestures_with_pause(self):
        steps = [0.05] * 12 + [0.0] * 15 + [0.05] * 12 + [0.0] * 15
        _, segs = run(make_frames(steps))
        self.assertEqual([s.reason for s in segs], [SegmentReason.IDLE] * 2)


if __name__ == "__main__":
    unittest.main()
