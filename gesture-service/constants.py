"""
Configuration constants for the Gesture Recognition Service.
"""

# --- Landmark buffer ---
# How many recent landmark frames to keep per session (sliding window).
# At ~10fps landmark transmission (see frontend), this covers ~3 seconds.
BUFFER_MAX_FRAMES = 30

# --- Gesture spotting (segmentation) ---
# Minimum number of consecutive "active motion" frames before a segment
# is considered a candidate gesture.
MIN_ACTIVE_FRAMES = 5

# Motion intensity threshold (normalized landmark displacement between
# consecutive frames) above which a frame is considered "active motion".
# Exact value is a placeholder — to be tuned once real data is available.
MOTION_THRESHOLD = 0.02

# How many consecutive "idle" (low-motion) frames end an active segment.
IDLE_FRAMES_TO_END_SEGMENT = 10

# --- Classification & SPOTER ---
# Confidence value returned by the mock classifier fallback.
MOCK_CONFIDENCE = 0.75

# SPOTER Model defaults
DEFAULT_SPOTER_MODEL_NAME = "spoter_arsl"
DEFAULT_SPOTER_MODEL_VERSION = "v1"
DEFAULT_SPOTER_CHECKPOINT_PATH = "models/spoter_arsl_v1.pth"
DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.3
# If the gap between top-1 and top-2 softmax probabilities is below this,
# the prediction is marked as ambiguous (KAN-24).
DEFAULT_AMBIGUITY_MARGIN = 0.15
# Number of top candidates to report when a prediction is ambiguous.
AMBIGUITY_TOP_K = 3
SPOTER_HIDDEN_DIM = 108
SPOTER_NUM_LANDMARKS = 54

# --- WebSocket / session ---
# How long (seconds) a session may remain idle before the server treats it
# as stale and clears its buffer.
SESSION_IDLE_TIMEOUT_SECONDS = 60
END_MOTION_THRESHOLD = 0.012
PRE_ROLL_FRAMES = 3
COARTICULATION_MIN_SEGMENT_FRAMES = 8
COARTICULATION_DIP_RATIO = 0.5
SEGMENT_MAX_FRAMES = 90

# --- Gloss sequence processing (KAN-18) ---
# Prediction below this confidence is dropped and recorded as a gap.
GLOSS_MIN_CONFIDENCE = 0.3
# Prediction below this confidence is kept but marked "uncertain".
GLOSS_ACCEPT_CONFIDENCE = 0.5
# The same gloss predicted again within this many ms is merged (repeat).
GLOSS_REPEAT_WINDOW_MS = 1000
# No gesture for this many ms ends the utterance (sentence).
GLOSS_UTTERANCE_PAUSE_MS = 2000
# An utterance is closed when it reaches this many glosses.
GLOSS_MAX_SEQUENCE_LENGTH = 20

# --- Continuous gesture processing (KAN-25) ---
# Temporal buffer keeps this many seconds of frames for re-classification
# and frame-drop recovery. Wider than the spotter's own segment buffer.
CONTINUOUS_TEMPORAL_BUFFER_SECONDS = 5.0
# Maximum gap (ms) between consecutive frames before interpolation is skipped.
# Gaps larger than this are treated as a discontinuity (e.g. tab-away).
CONTINUOUS_MAX_FRAME_GAP_MS = 500
# How many candidate gestures to keep in the streaming queue.
CONTINUOUS_CANDIDATE_QUEUE_SIZE = 10
# Minimum classification confidence for a candidate to be emitted.
# Below this, the candidate is dropped from the queue silently.
CONTINUOUS_MIN_CANDIDATE_CONFIDENCE = 0.25
# How many consecutive BAD-quality frames are tolerated (occlusion grace).
CONTINUOUS_OCCLUSION_GRACE_FRAMES = 5
# Minimum interval (ms) between partial (preview) emissions while a
# gesture is still in progress. 0 disables partial emissions.
CONTINUOUS_PARTIAL_EMIT_INTERVAL_MS = 500
# After classifying a segment, wait at least this long (ms) before
# re-classifying the same active segment for a partial update.
CONTINUOUS_RECLASS_COOLDOWN_MS = 300
# Landmark spread below which a hand is considered "collapsed" (blur).
CONTINUOUS_QUALITY_BLUR_THRESHOLD = 0.02

# --- Gesture lifecycle management (KAN-26) ---
# Normalized margin from frame edges defining the active camera area.
LIFECYCLE_ACTIVE_AREA_MARGIN = 0.08
# Minimum horizontal shoulder span (normalized) to consider signer positioned.
LIFECYCLE_MIN_SHOULDER_SPAN = 0.08
# How long (ms) the signer must be positioned before entering READY/SIGNING.
LIFECYCLE_START_HOLD_MS = 200
# Inactivity period (ms) before transitioning from SIGNING to INACTIVE.
LIFECYCLE_INACTIVITY_MS = 1200
# Inactivity threshold (ms) before auto-finalizing the current sentence.
LIFECYCLE_FINALIZE_TIMEOUT_MS = 2000
# Consecutive neutral-pose frames while signing that signal end of signing.
LIFECYCLE_NEUTRAL_END_FRAMES = 6

# --- Edge cases & error recovery (KAN-27) ---
# Inter-frame displacement above which a frame is treated as severe motion blur.
EDGE_SEVERE_BLUR_MOTION_THRESHOLD = 0.35
# Consecutive blurred frames before emitting a warning.
EDGE_BLUR_STREAK_TO_WARN = 2
# Consecutive degraded/bad frames before emitting a partial-occlusion warning.
EDGE_OCCLUSION_STREAK_TO_WARN = 6
# Consecutive out-of-bounds frames before emitting a user-out-of-frame warning.
EDGE_OUT_OF_FRAME_STREAK_TO_WARN = 5
# Max normalized distance from shoulder midpoint before a hand is extraneous.
EDGE_MAX_HAND_SHOULDER_DISTANCE = 0.85
# Minimum usable-frame quality ratio required to classify a segment.
EDGE_MIN_GOOD_FRAME_RATIO = 0.4
# Minimum net hand displacement across a segment to rule out fidgeting/jitter.
EDGE_MIN_NET_DISPLACEMENT = 0.04
# Minimum interval (ms) between repeated warnings of the same code.
EDGE_WARNING_COOLDOWN_MS = 2000

# --- NLP layer / LLM (KAN-19) ---
# Provider selected by the LLM_PROVIDER environment variable ("gemini" or "none").
DEFAULT_LLM_PROVIDER = "gemini"
DEFAULT_LLM_MODEL = "gemini-3.5-flash-lite"
# Seconds to wait for the LLM answer before falling back to plain glosses.
DEFAULT_LLM_TIMEOUT_SECONDS = 10.0
# Extra attempts on rate limit (429), server errors and timeouts.
LLM_MAX_RETRIES = 1
# Low temperature: translation, not creative writing.
LLM_TEMPERATURE = 0.2
# How many earlier sentences of the session are given to the model as context.
NLP_CONTEXT_SENTENCES = 3
# A sentence longer than this many words per gloss (+4) is rejected as invented content.
NLP_MAX_WORDS_PER_GLOSS = 3
