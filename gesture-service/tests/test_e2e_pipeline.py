"""End-to-End System Integration tests (KAN-28).

Verifies the full recognition pipeline over WebSocket:
  Landmarks -> EdgeCaseGuard -> ContinuousGestureProcessor (Spotting) ->
  Classification -> GlossSequence -> NLPService -> Armenian Sentence ->
  BackendPersistenceClient (Next.js / PostgreSQL internal API).
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

import main
from backend_persistence import BackendPersistenceClient, resolve_backend_base_url
from classification import ClassificationResult
from nlp import SentenceResult, SentenceStatus


def _hand(x: float, y: float) -> list[dict]:
    return [{"x": x + 0.01 * i, "y": y + 0.01 * i, "z": 0.0} for i in range(21)]


def _pose(wrist_y: float = 0.4) -> list[dict]:
    pts = [{"x": 0.5, "y": 0.3, "z": 0.0} for _ in range(33)]
    pts[11] = {"x": 0.4, "y": 0.35, "z": 0.0}
    pts[12] = {"x": 0.6, "y": 0.35, "z": 0.0}
    pts[23]["y"] = pts[24]["y"] = 0.7
    pts[15]["y"] = pts[16]["y"] = wrist_y
    return pts


def _landmarks_msg(session_id: str, ts: int, x: float, y: float, *, neutral: bool = False) -> dict:
    return {
        "type": "landmarks",
        "sessionId": session_id,
        "timestamp": ts,
        "leftHand": _hand(0.35, 0.45),
        "rightHand": _hand(x, y),
        "pose": _pose(wrist_y=0.9 if neutral else 0.4),
    }


class TestBackendPersistenceClient(unittest.TestCase):
    def test_resolve_backend_base_url_from_log_url(self):
        with patch.dict(
            os.environ,
            {"BACKEND_BASE_URL": "", "BACKEND_LOG_URL": "http://localhost:3000/api/internal/logs"},
            clear=False,
        ):
            self.assertEqual(resolve_backend_base_url(), "http://localhost:3000")

    def test_resolve_backend_base_url_explicit_override(self):
        with patch.dict(
            os.environ,
            {
                "BACKEND_BASE_URL": "http://web:3000/",
                "BACKEND_LOG_URL": "http://localhost:3000/api/internal/logs",
            },
            clear=False,
        ):
            self.assertEqual(resolve_backend_base_url(), "http://web:3000")

    def test_record_gesture_and_caption_enqueue(self):
        client = BackendPersistenceClient(base_url="http://localhost:3000", service_key="k")
        self.assertTrue(client.enabled)
        with patch.object(client, "_enqueue") as mock_enqueue:
            client.record_gesture("sess-1", "ԲԱՐԵՒ", 0.91)
            client.record_caption("sess-1", "Բարև ձեզ։", ["ԲԱՐԵՒ"], 0.91)

        self.assertEqual(mock_enqueue.call_count, 2)
        g_path, g_payload = mock_enqueue.call_args_list[0].args
        self.assertEqual(g_path, "/api/internal/sessions/sess-1/gestures")
        self.assertEqual(g_payload, {"gloss": "ԲԱՐԵՒ", "confidence": 0.91})

        c_path, c_payload = mock_enqueue.call_args_list[1].args
        self.assertEqual(c_path, "/api/internal/sessions/sess-1/captions")
        self.assertEqual(
            c_payload,
            {"text": "Բարև ձեզ։", "glosses": ["ԲԱՐԵՒ"], "confidence": 0.91},
        )


class TestEndToEndWebSocketPipeline(unittest.TestCase):
    def test_full_pipeline_connect_sign_finalize_sentence_and_persist(self):
        session_id = "e2e-session-1"
        fake_result = ClassificationResult(
            text="ԲԱՐԵՒ",
            gloss=["ԲԱՐԵՒ"],
            confidence=0.92,
            model_name="spoter_arsl",
            model_version="v1",
        )
        fake_sentence = SentenceResult(
            session_id=session_id,
            utterance_id=1,
            text="Բարև ձեզ։",
            status=SentenceStatus.OK,
            gloss_text="ԲԱՐԵՒ",
            warnings=[],
            provider="gemini",
            model="gemini-3.5-flash-lite",
            latency_ms=12,
        )

        with (
            patch("continuous.classify_segment", return_value=fake_result),
            patch("main.classify_segment", return_value=fake_result),
            patch.object(main.nlp_service, "generate", new=AsyncMock(return_value=fake_sentence)),
            patch.object(main.persistence, "record_gesture", new=MagicMock()) as mock_rec_gesture,
            patch.object(main.persistence, "record_caption", new=MagicMock()) as mock_rec_caption,
        ):
            client = TestClient(main.app)
            with client.websocket_connect("/ws") as ws:
                # 1. Connect handshake
                ws.send_json({"type": "connect", "sessionId": session_id})
                m_state = ws.receive_json()
                m_life = ws.receive_json()
                self.assertEqual(m_state, {"type": "state", "state": "listening"})
                self.assertEqual(m_life["type"], "lifecycle")
                self.assertEqual(m_life["sessionId"], session_id)
                self.assertEqual(m_life["phase"], "idle")

                # 2. Stream positioning + active signing frames
                ws.send_json(_landmarks_msg(session_id, 0, 0.50, 0.45))
                ws.send_json(_landmarks_msg(session_id, 250, 0.50, 0.45))
                for i in range(1, 8):
                    ws.send_json(
                        _landmarks_msg(
                            session_id,
                            250 + i * 50,
                            0.50 + 0.03 * i,
                            0.45 - 0.02 * i,
                        )
                    )

                # 3. Trigger edge-case warning (poor illumination) without breaking pipeline
                warn_msg = _landmarks_msg(session_id, 700, 0.68, 0.35)
                warn_msg["poorIllumination"] = True
                ws.send_json(warn_msg)

                # 4. Finalize utterance and drain emitted messages
                ws.send_json({"type": "finalize", "sessionId": session_id})

                received = []
                for _ in range(20):
                    msg = ws.receive_json()
                    received.append(msg)
                    if msg.get("type") == "lifecycle" and msg.get("phase") == "idle":
                        # Check if sentence already arrived before breaking
                        if any(m.get("type") == "sentence" for m in received):
                            break
                    if any(m.get("type") == "sentence" for m in received) and any(
                        m.get("type") == "state" and m.get("state") == "listening"
                        for m in received[1:]
                    ):
                        break

                types = [m["type"] for m in received]
                self.assertIn("warning", types)
                self.assertIn("caption", types)
                self.assertIn("gloss_sequence", types)
                self.assertIn("sentence", types)

                warning_ev = next(m for m in received if m["type"] == "warning")
                self.assertEqual(warning_ev["code"], "poor_illumination")

                caption_ev = next(m for m in received if m["type"] == "caption")
                self.assertEqual(caption_ev["gloss"], ["ԲԱՐԵՒ"])

                seq_ev = next(m for m in received if m["type"] == "gloss_sequence")
                self.assertEqual(seq_ev["sessionId"], session_id)
                self.assertEqual(seq_ev["utteranceId"], 1)

                sent_ev = next(m for m in received if m["type"] == "sentence")
                self.assertEqual(sent_ev["sessionId"], session_id)
                self.assertEqual(sent_ev["text"], "Բարև ձեզ։")
                self.assertEqual(sent_ev["status"], "ok")

                self.assertGreaterEqual(mock_rec_gesture.call_count, 1)
                self.assertEqual(mock_rec_gesture.call_args.args[0], session_id)
                mock_rec_caption.assert_called_once()
                self.assertEqual(mock_rec_caption.call_args.args[0], session_id)
                self.assertEqual(mock_rec_caption.call_args.args[1], "Բարև ձեզ։")

                # 5. Restart resets session cleanly
                ws.send_json({"type": "restart", "sessionId": session_id})
                r1 = ws.receive_json()
                r2 = ws.receive_json()
                r3 = ws.receive_json()
                self.assertEqual(r1["type"], "lifecycle")
                self.assertEqual(r1["phase"], "terminated")
                self.assertEqual(r2, {"type": "state", "state": "listening"})
                self.assertEqual(r3["type"], "lifecycle")
                self.assertEqual(r3["phase"], "idle")


if __name__ == "__main__":
    unittest.main()
