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

## Gloss Sequence Processing (KAN-18)

Between classification and the NLP/LLM layer, the service collects the
glosses predicted for each gesture segment into an ordered **gloss
sequence** per utterance (sentence). Implemented in
`gesture-service/gloss_sequence.py`. The existing `caption` and
`unrecognized` messages are unchanged; `gloss_sequence` is an additional
message.

### `gloss_sequence`
Sent when an utterance ends. This is the structured input for the NLP/LLM
layer.
```json
{
  "type": "gloss_sequence",
  "sessionId": "a1b2c3d4-...",
  "utteranceId": 1,
  "glosses": [
    {
      "gloss": "ԲԱՐԵՒ",
      "confidence": 0.91,
      "startMs": 1730000000000,
      "endMs": 1730000000900,
      "status": "accepted",
      "repeats": 1
    },
    {
      "gloss": "ԵՍ",
      "confidence": 0.42,
      "startMs": 1730000001800,
      "endMs": 1730000002500,
      "status": "uncertain",
      "repeats": 2
    }
  ],
  "glossText": "ԲԱՐԵՒ ԵՍ",
  "gaps": [1],
  "startMs": 1730000000000,
  "endMs": 1730000002500,
  "boundary": "pause"
}
```

| Field | Meaning |
|---|---|
| `sessionId` | Recognition session the sequence belongs to (same as in the client messages). |
| `utteranceId` | Counter of utterances within the session, starting at 1. |
| `glosses` | Glosses in temporal order (by `startMs`). |
| `glosses[].gloss` | Armenian gloss from the label map. |
| `glosses[].confidence` | Softmax confidence of the prediction (0..1). For merged repeats, the highest value. |
| `glosses[].startMs`, `endMs` | Start and end of the gesture segment, in the client `timestamp` units (ms). |
| `glosses[].status` | `accepted` (confident) or `uncertain` (low confidence, kept so the NLP layer can decide). |
| `glosses[].repeats` | How many predictions were merged into this gloss (`1` = no repeat). |
| `glossText` | The glosses joined with spaces, for convenience. |
| `gaps` | Positions of missing predictions: a value `g` means one or more segments were not recognized right before `glosses[g]` (`g` equal to the number of glosses means after the last one). Empty when nothing is missing. |
| `startMs`, `endMs` | Start of the first and end of the last gloss. |
| `boundary` | Why the utterance ended: `pause`, `finalize` or `max_length`. |

### Processing rules

Configured in `gesture-service/constants.py`:

| Rule | Constant | Default |
|---|---|---|
| Prediction below this confidence is dropped and recorded as a gap | `GLOSS_MIN_CONFIDENCE` | 0.3 |
| Prediction below this confidence is kept with `status: "uncertain"` | `GLOSS_ACCEPT_CONFIDENCE` | 0.5 |
| The same gloss predicted again within this time after the previous one is merged into it (`repeats` increases); a later one is a new gloss | `GLOSS_REPEAT_WINDOW_MS` | 1000 |
| Utterance ends after this time without a gesture (a gesture in progress never ends it) | `GLOSS_UTTERANCE_PAUSE_MS` | 2000 |
| Utterance ends when it reaches this number of glosses | `GLOSS_MAX_SEQUENCE_LENGTH` | 20 |

- A segment that is not recognized (`unrecognized`) is recorded as a gap in the open utterance.
- An utterance with no recognized glosses produces no `gloss_sequence` message.
- A `finalize` request closes the open utterance (`boundary: "finalize"`). The
  `gloss_sequence` message is sent after the `caption` and before the final
  `listening` state.
- Sequences are bound to the session of the connection that produced them;
  an unfinished utterance is dropped when the connection closes.

## Notes for Backend Implementation

- A mock server implementing this contract is available at
  `gesture-service/main.py` for frontend integration testing. It should be
  replaced with the real Gesture Spotting / SPOTER Classification / LLM
  pipeline, keeping the message shapes above unchanged where possible.
- The frontend treats `sessionId` as opaque; the backend may use it to
  maintain per-session buffers/state across the `landmarks` stream.