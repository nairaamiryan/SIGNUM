# WebSocket Communication Contract

This document defines the real-time communication protocol between the
**Next.js Frontend** and the **FastAPI Gesture Recognition Service**.

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

### `repeat`
Sent when the user requests re-evaluation of the most recently spotted gesture segment.
```json
{
  "type": "repeat",
  "sessionId": "a1b2c3d4-..."
}
```

### `restart`
Sent when the user restarts the current sentence (clears the buffer, spotter, and open gloss sequence).
```json
{
  "type": "restart",
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
Sent after a gesture segment (or `finalize` / `repeat` request) completes successfully. When top candidate signs have similar confidence (difference below `SPOTER_AMBIGUITY_MARGIN`), `ambiguous` is `true` and `candidates` lists the top-K candidates.
```json
{
  "type": "caption",
  "text": "Ես ջուր եմ ուզում։",
  "gloss": ["ԵՍ", "ՋՈՒՐ", "ՈՒԶԵԼ"],
  "confidence": 0.92,
  "ambiguous": false,
  "candidates": []
}
```

### `unrecognized`
Sent when a gesture segment could not be confidently classified. The
frontend displays a visual warning and does not update the caption.
```json
{ "type": "unrecognized" }
```

### `partial_caption`
Sent periodically while a gesture is still in progress, providing an
early preview of the recognition result. The frontend may display this
as a tentative/greyed-out caption. The result is not final and will be
superseded by a full `caption` when the gesture segment completes.
```json
{
  "type": "partial_caption",
  "text": "ԲԱՐԵՎ",
  "gloss": ["ԲԱՐԵՎ"],
  "confidence": 0.68,
  "partial": true
}
```

Partial captions are emitted at most once every
`CONTINUOUS_PARTIAL_EMIT_INTERVAL_MS` (default 500ms). They are part of
the continuous processing pipeline and require no action from
the frontend other than displaying them. When the gesture completes, a
normal `caption` message replaces the partial.

### `error`
Sent for any server-side error (e.g. malformed input, internal failure).
```json
{ "type": "error", "message": "Human-readable error description" }
```

### `lifecycle`
Sent when the signing-sequence lifecycle transitions between phases,
keeping the recognition pipeline and frontend synchronized.
```json
{
  "type": "lifecycle",
  "sessionId": "a1b2c3d4-...",
  "phase": "signing",
  "reason": "active_signing",
  "signerPresent": true,
  "signerPositioned": true,
  "inactivityMs": 0
}
```

| Field | Meaning |
|---|---|
| `phase` | `idle` (no signer positioned), `ready` (positioned in active camera area), `signing` (active signing/progression), `inactive` (inactivity period / neutral posture), `finalizing` (sentence finalization), or `terminated` (manual termination via `restart`). |
| `reason` | Machine-readable transition reason (e.g., `signer_positioned`, `active_signing`, `inactivity_period`, `neutral_posture`, `inactivity_timeout`, `manual_finalize`, `manual_termination`). |
| `signerPresent` | Whether any hand or upper-body pose landmarks are detected. |
| `signerPositioned` | Whether the signer is positioned within the active camera area (`LIFECYCLE_ACTIVE_AREA_MARGIN`). |
| `inactivityMs` | Elapsed inactivity duration in milliseconds since last active signing. |

### `warning`
Sent when a recoverable environmental or tracking edge case is detected
(e.g. poor illumination, severe motion blur, partial occlusion, user out of
frame, multiple people, extraneous hands, non-signing movement, or a
recoverable service error).
```json
{
  "type": "warning",
  "code": "poor_illumination",
  "recoverable": true
}
```

## Gloss Sequence Processing

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
| `glosses[].status` | `accepted` (confident), `uncertain` (low confidence), or `ambiguous` (multiple close candidates, kept so the NLP layer can disambiguate). |
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

## Sentence Generation

The NLP layer turns the gloss sequence of an utterance (see the section
above) into one grammatically correct Armenian sentence using a language
model. It lives in `gesture-service/nlp/` and is separated from the gesture
recognition pipeline: it only reads the finished `gloss_sequence`, and the
language model sits behind the `LLMProvider` interface, so the provider
(Gemini, Claude, GPT, ...) can be replaced without touching classification.

### `sentence`
Sent after the `gloss_sequence` of the same utterance. It is generated in the
background (usually 1-3 seconds), so it arrives later than the
`gloss_sequence`; match the two by `utteranceId`.
```json
{
  "type": "sentence",
  "sessionId": "a1b2c3d4-...",
  "utteranceId": 1,
  "text": "Ես ջուր եմ ուզում։",
  "status": "ok",
  "glossText": "ԵՍ ՋՈՒՐ ՈՒԶԵԼ",
  "warnings": [],
  "provider": "gemini",
  "model": "gemini-3.5-flash-lite",
  "latencyMs": 940
}
```

| Field | Meaning |
|---|---|
| `text` | The Armenian sentence. For `status: "fallback"` it is the plain gloss text instead. |
| `status` | `ok`, `partial` or `fallback` (see below). |
| `glossText` | The glosses the sentence was built from. |
| `warnings` | Reasons the result is not fully reliable (see below); empty for `ok`. |
| `provider`, `model` | The language model that produced the text (`null` when none was used). |
| `latencyMs` | Time spent generating the sentence. |

### Status

| Status | Meaning |
|---|---|
| `ok` | A sentence was generated from a complete, confident gloss sequence. |
| `partial` | A sentence was generated, but the input was incomplete or ambiguous, so it may not say everything the signer meant. The frontend should show it as tentative. |
| `fallback` | No usable sentence. `text` holds the plain glosses and `warnings` says why. |

### Warnings

| Warning | Meaning |
|---|---|
| `missing_glosses` | The gloss sequence had gaps (unrecognized signs). The model does not guess them. |
| `uncertain_glosses` | Some glosses had low confidence. |
| `ambiguous_glosses` | Some glosses had close candidate signs and were disambiguated using context. |
| `omitted_glosses` | The model left out glosses that did not fit. |
| `incomplete` | The model reports that the sentence does not express everything. |
| `llm_not_configured` | No language model is configured (`LLM_PROVIDER` / `GEMINI_API_KEY`). |
| `llm_timeout`, `llm_network`, `llm_rate_limited`, `llm_http_error`, `llm_blocked`, `llm_bad_response` | The language model call failed. |
| `invalid_output` | The answer was rejected: not valid JSON, not Armenian, contains digits that are not in the glosses, or is much longer than the glosses justify. |

### Rules

- The model may add only what Armenian grammar requires (function words, verb forms, case endings, punctuation). It must not add names, numbers, places, times, negation or any other information that is not in the glosses.
- A missing sign is never guessed. Low-confidence glosses are used only if they fit; otherwise they are left out and reported.
- The last 3 sentences of the session are given to the model as context (to resolve who is speaking or the tense) and are not copied.
- The call has a timeout (`LLM_TIMEOUT_SECONDS`, default 10) and one retry on rate limit or server errors. On any failure the `fallback` status is returned; the recognition itself is never blocked.
- One call is made per utterance, never per frame.

Configuration (environment variables, see `gesture-service/.env.example`):

| Variable | Purpose | Default |
|---|---|---|
| `LLM_PROVIDER` | `gemini`, or `none` to disable the NLP layer | `gemini` |
| `GEMINI_API_KEY` | API key (secret; set it in `.env` and on Render, never commit it) | - |
| `LLM_MODEL` | Gemini model id | `gemini-3.5-flash-lite` |
| `LLM_TIMEOUT_SECONDS` | Timeout of one LLM call | `10` |

## Notes for Backend Implementation

- A mock server implementing this contract is available at
  `gesture-service/main.py` for frontend integration testing. It should be
  replaced with the real Gesture Spotting / SPOTER Classification / LLM
  pipeline, keeping the message shapes above unchanged where possible.
- The frontend treats `sessionId` as opaque; the backend may use it to
  maintain per-session buffers/state across the `landmarks` stream.