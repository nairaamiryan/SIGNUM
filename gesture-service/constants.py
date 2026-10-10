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

# --- Classification (placeholder) ---
# Confidence value returned by the mock classifier.
MOCK_CONFIDENCE = 0.75

# --- WebSocket / session ---
# How long (seconds) a session may remain idle before the server treats it
# as stale and clears its buffer.
SESSION_IDLE_TIMEOUT_SECONDS = 60