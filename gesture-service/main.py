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

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend_log_handler import BackendLogHandler
from classification import ClassificationResult, classify_segment
from gloss_sequence import BOUNDARY_FINALIZE, GlossSequence
from landmark_buffer import LandmarkFrame
from nlp import NLPService, SentenceStatus
from session import RecognitionState, SessionRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("gesture-service")
logger.addHandler(BackendLogHandler())


@asynccontextmanager
async def lifespan(app: FastAPI):
    backend_url = os.environ.get("BACKEND_LOG_URL", "not configured")
    logger.info("=== Gesture Service starting ===")
    logger.info("Backend log forward endpoint: %s", backend_url)
    yield
    logger.info("=== Gesture Service shutting down ===")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = SessionRegistry()
nlp_service = NLPService.from_env()  # Armenian sentence generation (KAN-19)
_background_tasks: set = set()  # keeps running sentence tasks referenced


@app.get("/")
@app.get("/health")
async def health_check():
    logger.info("Health check ping received")
    return {
        "status": "ok",
        "service": "gesture-service",
        "active_sessions": registry.active_count()
        if hasattr(registry, "active_count")
        else "running",
    }


async def send_state(websocket: WebSocket, state: RecognitionState) -> None:
    await websocket.send_text(json.dumps({"type": "state", "state": state.value}))


def build_caption_payload(result: ClassificationResult) -> dict:
    """Build the `caption` WebSocket payload, including ambiguity metadata if present."""
    payload: dict = {
        "type": "caption",
        "text": result.text,
        "gloss": result.gloss,
        "confidence": result.confidence,
    }
    if result.is_ambiguous:
        payload["ambiguous"] = True
        payload["candidates"] = [c.to_dict() for c in result.candidates]
    return payload


async def emit_classification_result(
    websocket: WebSocket,
    session_id: str,
    result: ClassificationResult | None,
    context_label: str,
) -> None:
    """Send either `unrecognized` or `caption` over the WebSocket and log the result."""
    if result is None:
        await websocket.send_text(json.dumps({"type": "unrecognized"}))
        return

    logger.info(
        "%s: gloss=%s confidence=%.2f ambiguous=%s model=%s version=%s",
        context_label,
        result.gloss,
        result.confidence,
        result.is_ambiguous,
        result.model_name,
        result.model_version,
        extra={
            "session_id": session_id,
            "model_name": result.model_name,
            "model_version": result.model_version,
            "confidence": result.confidence,
            "ambiguous": result.is_ambiguous,
            "audit": True,
        },
    )
    await websocket.send_text(json.dumps(build_caption_payload(result)))


async def send_gloss_sequence(websocket: WebSocket, sequence: GlossSequence) -> None:
    await websocket.send_text(json.dumps(sequence.to_message()))


async def send_sentence(websocket: WebSocket, session, sequence: GlossSequence) -> None:
    """Generate the Armenian sentence of a finished utterance (KAN-19) and send it."""
    try:
        result = await nlp_service.generate(sequence, list(session.sentence_context))
        if result.status != SentenceStatus.FALLBACK:
            session.remember_sentence(result.text)
        await websocket.send_text(json.dumps(result.to_message()))
    except Exception:
        # For example the socket closed while the model was answering.
        logger.warning(
            "Could not deliver the sentence of utterance %s",
            sequence.utterance_id,
            exc_info=True,
            extra={"session_id": sequence.session_id},
        )


async def publish_gloss_sequence(websocket: WebSocket, session, sequence: GlossSequence) -> None:
    """Send the gloss sequence now; the sentence follows when the model answers."""
    await send_gloss_sequence(websocket, sequence)
    task = asyncio.create_task(send_sentence(websocket, session, sequence))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def parse_landmark_frame(message: dict) -> LandmarkFrame:
    return LandmarkFrame(
        timestamp=message["timestamp"],
        left_hand=message.get("leftHand"),
        right_hand=message.get("rightHand"),
        face=message.get("face"),
        pose=message.get("pose"),
    )


@app.websocket("/ws")
@app.websocket("/")
async def recognition_socket(websocket: WebSocket):
    await websocket.accept()
    client_info = (
        f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
    )
    logger.info("WebSocket connection accepted from client %s", client_info)
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
                logger.info(
                    "Session %s connected and set to LISTENING (client: %s)",
                    session_id,
                    client_info,
                    extra={"session_id": session_id, "audit": True},
                )
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

                # Gesture spotting: the spotter consumes each frame and emits
                # finished gesture segments, which go to classification.
                for segment in session.spotter.process(frame):
                    session.last_segment_frames = list(segment.frames)
                    seg_result = classify_segment(segment.frames)
                    closed = session.gloss_sequence.add_prediction(
                        seg_result,
                        segment.frames[0].timestamp,
                        segment.frames[-1].timestamp,
                    )
                    await emit_classification_result(
                        websocket, session_id, seg_result, "Gesture classified"
                    )
                    if closed is not None:
                        await publish_gloss_sequence(websocket, session, closed)

                # Utterance boundary: a pause with no gesture in progress.
                pause_closed = session.gloss_sequence.tick(
                    frame.timestamp, busy=session.spotter.is_active
                )
                if pause_closed is not None:
                    await publish_gloss_sequence(websocket, session, pause_closed)

            elif msg_type == "repeat":
                if not session.last_segment_frames:
                    await websocket.send_text(json.dumps({"type": "unrecognized"}))
                    continue

                session.gloss_sequence.remove_last_token()
                repeat_frames = session.last_segment_frames
                repeat_result = classify_segment(repeat_frames)
                closed = session.gloss_sequence.add_prediction(
                    repeat_result,
                    repeat_frames[0].timestamp,
                    repeat_frames[-1].timestamp,
                )
                await emit_classification_result(
                    websocket, session_id, repeat_result, "Repeat classified"
                )
                if closed is not None:
                    await publish_gloss_sequence(websocket, session, closed)

            elif msg_type == "restart":
                session.reset()
                logger.info(
                    "Session %s restarted by user",
                    session_id,
                    extra={"session_id": session_id, "audit": True},
                )
                await send_state(websocket, session.state)

            elif msg_type == "finalize":
                if session.buffer.is_empty:
                    await websocket.send_text(json.dumps({"type": "unrecognized"}))
                    continue

                session.state = RecognitionState.PROCESSING
                await send_state(websocket, session.state)

                # Close the segment still in progress; fall back to the buffer if none.
                open_segment = session.spotter.flush()
                final_frames = open_segment.frames if open_segment else session.buffer.frames()
                session.last_segment_frames = list(final_frames)
                result = classify_segment(final_frames)
                full_sequence = session.gloss_sequence.add_prediction(
                    result, final_frames[0].timestamp, final_frames[-1].timestamp
                )

                await emit_classification_result(
                    websocket, session_id, result, "Finalize classified"
                )

                # Finalize ends the utterance: send the structured gloss sequence.
                for finished in (full_sequence, session.gloss_sequence.close(BOUNDARY_FINALIZE)):
                    if finished is not None:
                        await publish_gloss_sequence(websocket, session, finished)

                session.reset()
                await send_state(websocket, session.state)

            else:
                logger.warning("Unknown message type: %s", msg_type)

    except WebSocketDisconnect:
        if session:
            registry.remove(session.session_id)
            logger.info(
                "Session %s disconnected",
                session.session_id,
                extra={"session_id": session.session_id, "audit": True},
            )
    except Exception:
        logger.exception("Unexpected error in recognition_socket")
        if session:
            registry.remove(session.session_id)
