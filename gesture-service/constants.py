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
