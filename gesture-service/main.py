"""
FastAPI WebSocket Gesture Recognition Service.

Implements the full recognition pipeline described in KAN-15:
  1. Receive landmark data from the frontend (landmark_buffer.py)
  2. Maintain a per-session sliding-window buffer
  3. Perform gesture spotting/segmentation (spotting.py)
  4. Pass detected gesture segments to classification (classification.py)
  5. Return recognized sign/gloss results over the same WebSocket
  6. Maintain recognition state and session lifecycle (session.py)

See docs/websocket-contract.md for the full message protocol.
"""

import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from classification import classify_segment
from landmark_buffer import LandmarkFrame
from session import RecognitionState, SessionRegistry
from spotting import is_segment_active, is_segment_idle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gesture-service")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = SessionRegistry()


async def send_state(websocket: WebSocket, state: RecognitionState) -> None:
    await websocket.send_text(json.dumps({"type": "state", "state": state.value}))


def parse_landmark_frame(message: dict) -> LandmarkFrame:
    return LandmarkFrame(
        timestamp=message["timestamp"],
        left_hand=message.get("leftHand"),
        right_hand=message.get("rightHand"),
        face=message.get("face"),
        pose=message.get("pose"),
    )


@app.websocket("/ws")
async def recognition_socket(websocket: WebSocket):
    await websocket.accept()
    session = None

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Received malformed JSON: %s", raw)
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Malformed message"})
                )
                continue

            msg_type = message.get("type")
            session_id = message.get("sessionId")

            if not session_id:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Missing sessionId"})
                )
                continue

            session = registry.get_or_create(session_id)
            session.touch()

            if msg_type == "connect":
                session.state = RecognitionState.LISTENING
                await send_state(websocket, session.state)

            elif msg_type == "landmarks":
                if session.state != RecognitionState.LISTENING:
                    # Ignore landmark frames while processing/error.
                    continue

                try:
                    frame = parse_landmark_frame(message)
                except (KeyError, TypeError) as exc:
                    logger.warning("Invalid landmarks payload: %s", exc)
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Invalid landmarks payload"})
                    )
                    continue

                session.buffer.add(frame)
                frames = session.buffer.frames()

                # Gesture spotting: flag unrecognized/noise segments that
                # never settle into a clean active->idle gesture cycle.
                if is_segment_active(frames) and is_segment_idle(frames[-5:]):
                    await websocket.send_text(json.dumps({"type": "unrecognized"}))

            elif msg_type == "finalize":
                if session.buffer.is_empty:
                    await websocket.send_text(json.dumps({"type": "unrecognized"}))
                    continue

                session.state = RecognitionState.PROCESSING
                await send_state(websocket, session.state)

                result = classify_segment(session.buffer.frames())

                if result is None:
                    await websocket.send_text(json.dumps({"type": "unrecognized"}))
                else:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "caption",
                                "text": result.text,
                                "gloss": result.gloss,
                                "confidence": result.confidence,
                            }
                        )
                    )

                session.reset()
                await send_state(websocket, session.state)

            else:
                logger.warning("Unknown message type: %s", msg_type)

    except WebSocketDisconnect:
        if session:
            registry.remove(session.session_id)
            logger.info("Session %s disconnected", session.session_id)
    except Exception:
        logger.exception("Unexpected error in recognition_socket")
        if session:
            registry.remove(session.session_id)