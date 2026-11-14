# SIGNUM

SIGNUM recognizes Armenian sign language from a camera. The browser extracts
MediaPipe landmarks (hands, pose, face), streams them to a gesture service over
WebSocket, and shows the recognized captions.

## Architecture

| Part | Folder | Stack | Role |
|---|---|---|---|
| Web app + API | `web/` | Next.js (App Router), TypeScript, Sequelize + PostgreSQL | UI, camera and landmark extraction, auth (JWT), sessions, logging endpoint |
| Gesture service | `gesture-service/` | Python, FastAPI, WebSocket | Receives landmark frames, spots gestures, classifies them, returns captions |
| Database | - | PostgreSQL | Users, sessions, recognition data |

Data flow: `browser (MediaPipe) -> WebSocket /ws -> gesture-service (spotting -> classification) -> caption -> browser`.
The gesture service forwards its logs to the web app (`POST /api/internal/logs`, protected by `x-service-key`).

### Gesture service pipeline

1. `landmark_buffer.py` - per-session sliding window of landmark frames.
2. `spotting.py` - `HeuristicGestureSpotter`: motion thresholds with hysteresis, pre-roll,
   co-articulation split, neutral-pose suppression, max segment length. It implements the
   `GestureSpotter` protocol, so a learned model can replace it later.
3. `classification.py` - runs the SPOTER model on a spotted segment and returns the predicted
   Armenian gloss with a softmax confidence score.
4. `session.py` - per-connection state; `main.py` - WebSocket endpoint.

### Gesture classification model

- Architecture: SPOTER (Sign Pose-based Transformer), loaded from a trained `.pth` checkpoint.
  The checkpoint is `gesture-service/models/spoter_arsl_v1.pth`, configured by
  `SPOTER_CHECKPOINT_PATH`.
- Input: tensor of shape `(T, 108)` - 54 MediaPipe landmarks (21 left hand, 21 right hand,
  12 upper-body pose points) with 2D `(x, y)` coordinates, after SPOTER hand/body normalization.
- Output: the predicted Armenian gloss and the softmax confidence.
- Label map: `gesture-service/data/label_map.json` (class index <-> Armenian gloss); it is also read
  from the checkpoint when it is stored there.
- Training data: Slovo MediaPipe landmarks (Russian Sign Language), restricted to a set of shared
  core signs and mapped to Armenian glosses (for example ԲԱՐԵՒ, ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ, ԵՍ, ՋՈՒՐ, ՈՒԶԵԼ).
  The model can later be extended with Armenian Sign Language video data
  (Wikimedia Commons, "Videos of Armenian Sign Language").
  The current checkpoint has 115 classes.
- Evaluation: top-1 / top-5 accuracy with `scripts/evaluate.py`
  (`python scripts/evaluate.py --checkpoint models/spoter_arsl_v1.pth --test_data data/test.pt`).
  Current result of `spoter_arsl_v1` on the 30-sample test set (115 classes): **top-1 0.00%, top-5 3.33%**.
  This first checkpoint was trained on a very small subset (about one sample per class) and is not
  usable for real recognition yet; it must be retrained on the full prepared dataset before production use.
- Fallback: if the checkpoint file is missing, the service starts in a **mock mode** and returns
  fixed demo captions. Make sure the checkpoint is present in every deployment.
- Predictions below `SPOTER_CONFIDENCE_THRESHOLD` are treated as unrecognized.

### Training pipeline

All scripts are in `gesture-service/scripts/` (run `python scripts/<name>.py --help` for the options):

1. `download_dataset.py` - downloads the Slovo landmark data.
2. `prepare_dataset.py` - selects the shared signs, maps glosses to Armenian, builds the
   `(T, 108)` landmark tensors and writes `data/train.pt`, `data/test.pt`, `data/label_map.json`.
3. `train_spoter.py` - trains SPOTER and saves the checkpoint (`models/spoter_arsl_v1.pth`).
4. `evaluate.py` - computes top-1 / top-5 accuracy and per-class metrics.

## Requirements

- Node.js (LTS) and npm
- Python 3.10+
- PostgreSQL

## Local setup

### 1. Database

Create an empty PostgreSQL database and a user for it.

### 2. Web app

```bash
cd web
npm install
cp .env.local.example .env.local   # then fill in the values
npx sequelize-cli db:migrate
npm run dev                        # http://localhost:3000
```

Environment variables (see `web/.env.local.example`):

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_WS_URL` | WebSocket URL of the gesture service (`ws://localhost:8000/ws` locally) |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Secret for signing JWT tokens (long random string, 32+ chars) |
| `SERVICE_API_KEY` | Shared key for service-to-service calls (`x-service-key`); must match the gesture service |
| `LOG_LEVEL`, `LOG_DIR` | Log level and log directory |
| `LOG_MAX_SIZE_MB`, `LOG_RETENTION_DAYS` | Log rotation size and retention |
| `DB_SLOW_QUERY_MS` | Threshold for slow-query logging |

### 3. Gesture service

```bash
cd gesture-service
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1      Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env               # then fill in the values
uvicorn main:app --port 8000 --env-file .env --reload
```

The service listens on `ws://localhost:8000/ws`. Environment variables are documented in
`gesture-service/.env.example`:

| Variable | Purpose |
|---|---|
| `BACKEND_LOG_URL` | Web app endpoint that receives forwarded logs (`.../api/internal/logs`) |
| `SERVICE_API_KEY` | Same value as `SERVICE_API_KEY` in the web app |
| `MAX_MESSAGE_LEN` | Maximum WebSocket message length |
| `SPOTER_MODEL_NAME`, `SPOTER_MODEL_VERSION` | Model name and version |
| `SPOTER_CHECKPOINT_PATH` | Path to the trained checkpoint (`models/spoter_arsl_v1.pth`) |
| `SPOTER_CONFIDENCE_THRESHOLD` | Minimum confidence for a prediction to be accepted |

## Tests

```bash
cd gesture-service
python -m unittest discover -s tests
```

## Logging

Both services write to one daily log file `logs/signum-YYYY-MM-DD.log`:

```
[TIMESTAMP] [LEVEL] [COMPONENT] [AUDIT?] [SESSION_ID] Message
```

Files rotate by day and size, old files are zipped and removed after the retention period.

## Deployment

| Part | Platform |
|---|---|
| `web/` | Vercel |
| `gesture-service/` | Render |

Deploy the gesture service first, because the web app needs its public URL.

### Gesture service on Render

1. New -> Web Service, connect this repository.
2. Root Directory: `gesture-service`. Runtime: Python.
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Environment variables (Environment tab): every variable from `gesture-service/.env.example`
   (`BACKEND_LOG_URL`, `SERVICE_API_KEY`, `MAX_MESSAGE_LEN`, `SPOTER_MODEL_NAME`, `SPOTER_MODEL_VERSION`,
   `SPOTER_CHECKPOINT_PATH`, `SPOTER_CONFIDENCE_THRESHOLD`).
   `BACKEND_LOG_URL` must point to the deployed web app (`https://<vercel-domain>/api/internal/logs`) and
   `SERVICE_API_KEY` must equal the value set in Vercel.
   The checkpoint `gesture-service/models/spoter_arsl_v1.pth` must be in the repository (it is
   about 8 MB); otherwise the service silently runs in mock mode.
   Secret values are entered only in the Render dashboard, never committed.
6. After the deploy, the WebSocket URL is `wss://<service-name>.onrender.com/ws`.

### Web app on Vercel

1. Import the repository in Vercel.
2. Root Directory: `web`. Framework preset: Next.js.
3. Environment variables (Settings -> Environment Variables): all variables from
   `web/.env.local.example` (`DATABASE_URL`, `JWT_SECRET`, `SERVICE_API_KEY`, logging variables).
   `NEXT_PUBLIC_WS_URL` must point to the Render service: `wss://<service-name>.onrender.com/ws`.
   Note that `NEXT_PUBLIC_*` values are baked in at build time, so redeploy after changing it.
4. Every pull request gets a Preview deployment automatically; `main` is deployed to production.
5. Run database migrations against the production database before the first start:
   `npx sequelize-cli db:migrate` (with the production database variables set).

### Notes

- Render free instances sleep after inactivity, so the first WebSocket connection can be slow.
- `localhost` addresses do not work from a Vercel deployment; use the public Render URL.

## Conventions

- Dependencies are pinned to exact versions (no `^` or `~`).
- No hardcoded error strings; use the constants in `web/lib/constants.ts`.
- Validation schemas live in `web/lib/schemas.ts`.
- Environment values live in `.env` files with a committed `.env.example`; real `.env*` files are git-ignored.

## Credits

The gesture classifier is based on SPOTER (Sign Pose-based Transformer),
https://github.com/matyasbohacek/spoter (Apache-2.0), trained on the Slovo dataset
(https://github.com/ai-forever/slovo, CC BY-SA 4.0) and mapped to Armenian glosses.