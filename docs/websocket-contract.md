# WebSocket Communication Contract

This document defines the real-time communication protocol between the
**Next.js Frontend** and the **FastAPI Gesture Recognition Service**, as
implemented in KAN-14.

- **Endpoint:** `ws://<gesture-service-host>/ws` (configured via
  `NEXT_PUBLIC_WS_URL` on the frontend)
- **Transport:** WebSocket, text frames, JSON-encoded payloads
- **Session model:** One WebSocket connection per recognition session. The
  frontend generates a `sessionId` (UUID) when `connect()` is called and
  includes it on every outgoing message.

## Connection Lifecycle

1. Frontend opens the WebSocket connection.
2. On `open`, frontend sends a `connect` message with the session ID.
3. Server acknowledges by sending a `state` message (`listening`).
4. Frontend streams `landmarks` messages continuously (~10 fps) while the
   camera is active.
5. User triggers `finalize`; server responds with a `processing` state,
   followed by a `caption` result, followed by a `listening` state.
6. Frontend closes the connection when the camera is stopped
   (`disconnect()`).

If the connection drops unexpectedly, the frontend attempts to reconnect
up to 3 times with exponential backoff (1s, 2s, 4s) before surfacing a
connection error to the user.

## Client → Server Messages

### `connect`
Sent once, immediately after the socket opens.
```json
{
  "type": "connect",
  "sessionId": "a1b2c3d4-..."
}
```

### `landmarks`
Sent continuously (~every 100ms) while listening. Coordinates are
normalized (MediaPipe Holistic output: x, y, z in [0, 1] relative to
frame dimensions).
```json
{
  "type": "landmarks",
  "sessionId": "a1b2c3d4-...",
  "timestamp": 1730000000000,
  "leftHand": [{ "x": 0.42, "y": 0.61, "z": -0.02 }, ...] ,
  "rightHand": null,
  "face": [{ "x": 0.50, "y": 0.30, "z": 0.00 }, ...],
  "pose": [{ "x": 0.48, "y": 0.55, "z": 0.01 }, ...]
}
```
- `leftHand` / `rightHand`: 21 points each, or `null` if the hand is not
  visible in the frame.
- `face`: subset of face landmarks relevant to non-manual grammatical
  markers, or `null` if not detected.
- `pose`: upper-body pose landmarks, or `null` if not detected.
- Exact point count/selection is not finalized — it will be adjusted to
  match the SPOTER model's input requirements once defined.

### `finalize`
Sent when the user explicitly ends the current sentence.
```json
{
  "type": "finalize",
  "sessionId": "a1b2c3d4-..."
}
```

## Server → Client Messages

### `state`
Informs the frontend of the current recognition state.
```json
{ "type": "state", "state": "idle" | "listening" | "processing" | "error" }
```

### `caption`
Sent after a `finalize` request completes successfully.
```json
{
  "type": "caption",
  "text": "Ես ջուր եմ ուզում։",
  "gloss": ["ԵՍ", "ՋՈՒՐ", "ՈՒԶԵԼ"],
  "confidence": 0.92
}
```

### `unrecognized`
Sent when a gesture segment could not be confidently classified. The
frontend displays a visual warning and does not update the caption.
```json
{ "type": "unrecognized" }
```

### `error`
Sent for any server-side error (e.g. malformed input, internal failure).
```json
{ "type": "error", "message": "Human-readable error description" }
```

## Notes for Backend Implementation

- A mock server implementing this contract is available at
  `gesture-service/main.py` for frontend integration testing. It should be
  replaced with the real Gesture Spotting / SPOTER Classification / LLM
  pipeline, keeping the message shapes above unchanged where possible.
- The frontend treats `sessionId` as opaque; the backend may use it to
  maintain per-session buffers/state across the `landmarks` stream.