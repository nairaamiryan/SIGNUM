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

