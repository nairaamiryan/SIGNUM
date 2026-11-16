"""Tests for gloss sequence processing (KAN-18)."""

import unittest
from dataclasses import dataclass

from gloss_sequence import (
    BOUNDARY_FINALIZE,
    BOUNDARY_MAX_LENGTH,
    BOUNDARY_PAUSE,
    STATUS_ACCEPTED,
    STATUS_UNCERTAIN,
    GlossSequenceProcessor,
)


@dataclass
class Pred:
    gloss: list
    confidence: float


def make(**kwargs) -> GlossSequenceProcessor:
    return GlossSequenceProcessor("s1", **kwargs)


class GlossSequenceTests(unittest.TestCase):
    def test_keeps_temporal_order_and_session(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        p.add_prediction(Pred(["B"], 0.9), 1000, 1500)
        p.add_prediction(Pred(["C"], 0.9), 2000, 2500)
        seq = p.close(BOUNDARY_FINALIZE)
        self.assertEqual([t.gloss for t in seq.tokens], ["A", "B", "C"])
        self.assertEqual(seq.session_id, "s1")
        self.assertEqual(seq.gloss_text, "A B C")
        self.assertEqual((seq.start_ms, seq.end_ms), (0, 2500))

    def test_late_prediction_is_put_in_order(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        p.add_prediction(Pred(["C"], 0.9), 4000, 4500)
        p.add_prediction(Pred(["B"], 0.9), 2000, 2500)
        seq = p.close()
        self.assertEqual([t.gloss for t in seq.tokens], ["A", "B", "C"])

    def test_low_confidence_is_dropped_and_recorded_as_gap(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        p.add_prediction(Pred(["X"], 0.1), 1000, 1500)  # below min
        p.add_prediction(Pred(["B"], 0.9), 2000, 2500)
        seq = p.close()
        self.assertEqual([t.gloss for t in seq.tokens], ["A", "B"])
        self.assertEqual(seq.gaps, [1])

    def test_unrecognized_segment_is_a_gap(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        p.add_prediction(None, 1000, 1500)
        p.add_prediction(None, 2000, 2500)  # same position: one marker
        seq = p.close()
        self.assertEqual(seq.gaps, [1])

    def test_uncertain_band(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.4), 0, 500)
        p.add_prediction(Pred(["B"], 0.8), 1000, 1500)
        seq = p.close()
        self.assertEqual(seq.tokens[0].status, STATUS_UNCERTAIN)
        self.assertEqual(seq.tokens[1].status, STATUS_ACCEPTED)

    def test_repeat_inside_window_is_merged(self):
        p = make(repeat_window_ms=1000)
        p.add_prediction(Pred(["A"], 0.6), 0, 500)
        p.add_prediction(Pred(["A"], 0.9), 1000, 1500)  # gap 500 ms
        seq = p.close()
        self.assertEqual(len(seq.tokens), 1)
        token = seq.tokens[0]
        self.assertEqual(token.repeats, 2)
        self.assertEqual(token.confidence, 0.9)
        self.assertEqual(token.status, STATUS_ACCEPTED)
        self.assertEqual((token.start_ms, token.end_ms), (0, 1500))

    def test_repeat_after_window_is_kept(self):
        p = make(repeat_window_ms=1000)
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        p.add_prediction(Pred(["A"], 0.9), 3000, 3500)  # a real second sign
        seq = p.close()
        self.assertEqual([t.gloss for t in seq.tokens], ["A", "A"])

    def test_overlapping_duplicate_is_merged(self):
        # finalize may re-classify frames that were already spotted
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 1000, 2000)
        p.add_prediction(Pred(["A"], 0.8), 500, 2200)
        seq = p.close()
        self.assertEqual(len(seq.tokens), 1)
        self.assertEqual(seq.tokens[0].start_ms, 500)

    def test_multi_gloss_prediction(self):
        p = make()
        p.add_prediction(Pred(["A", "B", "C"], 0.75), 0, 900)
        seq = p.close()
        self.assertEqual([t.gloss for t in seq.tokens], ["A", "B", "C"])

    def test_pause_closes_utterance(self):
        p = make(pause_ms=2000)
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        self.assertIsNone(p.tick(1500))
        seq = p.tick(2500)
        self.assertIsNotNone(seq)
        self.assertEqual(seq.boundary, BOUNDARY_PAUSE)
        self.assertFalse(p.has_pending)
        self.assertIsNone(p.tick(9000))

    def test_busy_gesture_blocks_pause(self):
        p = make(pause_ms=2000)
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        self.assertIsNone(p.tick(10000, busy=True))
        self.assertTrue(p.has_pending)

    def test_max_length_closes_utterance(self):
        p = make(max_length=2)
        self.assertIsNone(p.add_prediction(Pred(["A"], 0.9), 0, 500))
        seq = p.add_prediction(Pred(["B"], 0.9), 1000, 1500)
        self.assertIsNotNone(seq)
        self.assertEqual(seq.boundary, BOUNDARY_MAX_LENGTH)
        self.assertFalse(p.has_pending)

    def test_close_with_nothing_returns_none(self):
        p = make()
        self.assertIsNone(p.close())
        p.add_prediction(None, 0, 500)
        self.assertIsNone(p.close())  # only gaps: nothing to send
        self.assertFalse(p.has_pending)

    def test_utterance_ids_increase_per_session(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        first = p.close()
        p.add_prediction(Pred(["B"], 0.9), 5000, 5500)
        second = p.close()
        self.assertEqual((first.utterance_id, second.utterance_id), (1, 2))

    def test_discard_drops_open_utterance(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        p.discard()
        self.assertFalse(p.has_pending)
        self.assertIsNone(p.close())

    def test_message_format(self):
        p = make()
        p.add_prediction(Pred(["A"], 0.9), 0, 500)
        p.add_prediction(None, 1000, 1500)
        p.add_prediction(Pred(["B"], 0.45), 2000, 2500)
        msg = p.close(BOUNDARY_FINALIZE).to_message()
        self.assertEqual(msg["type"], "gloss_sequence")
        self.assertEqual(msg["sessionId"], "s1")
        self.assertEqual(msg["utteranceId"], 1)
        self.assertEqual(msg["glossText"], "A B")
        self.assertEqual(msg["gaps"], [1])
        self.assertEqual(msg["boundary"], "finalize")
        self.assertEqual((msg["startMs"], msg["endMs"]), (0, 2500))
        self.assertEqual(
            msg["glosses"][1],
            {
                "gloss": "B",
                "confidence": 0.45,
                "startMs": 2000,
                "endMs": 2500,
                "status": "uncertain",
                "repeats": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
