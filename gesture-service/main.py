"""
Minimal FastAPI WebSocket stub for the Gesture Recognition Service.

This mocks the real-time recognition flow described in KAN-14 so the
frontend's WebSocket integration (connect / landmarks / finalize) can be
tested end-to-end before the actual MediaPipe → SPOTER → LLM pipeline is
implemented.
"""

import asyncio
import json
import random

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fake gloss/caption pairs returned when the client finalizes a sentence.
MOCK_RESULTS = [
    {"gloss": ["ԵՍ", "ՋՈՒՐ", "ՈՒԶԵԼ"], "text": "Ես ջուր եմ ուզում։", "confidence": 0.92},
    {"gloss": ["ԲԱՐԵՒ"], "text": "Բարև։", "confidence": 0.88},
    {"gloss": ["ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ"], "text": "Շնորհակալություն։", "confidence": 0.95},
]


@app.websocket("/ws")
async def recognition_socket(websocket: WebSocket):
    await websocket.accept()
    landmark_count = 0

    try:
        while True:
            raw = await websocket.receive_text()
            message = json.loads(raw)
            msg_type = message.get("type")

            if msg_type == "connect":
                await websocket.send_text(
                    json.dumps({"type": "state", "state": "listening"})
                )

            elif msg_type == "landmarks":
                landmark_count += 1
                # Simulate occasional unrecognized gestures for UI testing.
                if landmark_count % 50 == 0:
                    await websocket.send_text(
                        json.dumps({"type": "unrecognized"})
                    )

            elif msg_type == "finalize":
                await websocket.send_text(
                    json.dumps({"type": "state", "state": "processing"})
                )
                await asyncio.sleep(1.5)  # simulate processing latency

                result = random.choice(MOCK_RESULTS)
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "caption",
                            "text": result["text"],
                            "gloss": result["gloss"],
                            "confidence": result["confidence"],
                        }
                    )
                )
                await websocket.send_text(
                    json.dumps({"type": "state", "state": "listening"})
                )
                landmark_count = 0

    except WebSocketDisconnect:
        pass