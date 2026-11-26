export const ConnectionState = {
    IDLE: "idle",
    CONNECTING: "connecting",
    OPEN: "open",
    RECONNECTING: "reconnecting",
    CLOSED: "closed",
    FAILED: "failed",
} as const;

export const ServerState = {
    IDLE: "idle",
    LISTENING: "listening",
    PROCESSING: "processing",
    ERROR: "error",
} as const;

export const MAX_RECONNECT_ATTEMPTS = 3;
export const RECONNECT_BASE_DELAY_MS = 1000; // 1s, 2s, 4s backoff
export const RECONNECT_BACKOFF_MULTIPLIER = 2;

export const ERROR_MESSAGES = {
    UNAUTHORIZED: "Unauthorized",
    INVALID_INPUT: "Invalid input",
    INVALID_CREDENTIALS: "Invalid credentials",
    EMAIL_ALREADY_REGISTERED: "Email already registered",
    NOT_FOUND: "Not found",
    SESSION_NOT_FOUND: "Session not found",
} as const;

// --- Real-time captioning (KAN-23) ---
export const SentenceStatus = {
    OK: "ok",
    PARTIAL: "partial",
    FALLBACK: "fallback",
} as const;

export const GlossStatus = {
    ACCEPTED: "accepted",
    UNCERTAIN: "uncertain",
} as const;

export const CAPTION_HISTORY_LIMIT = 5; // completed captions kept on screen
export const MAX_PARTIAL_GLOSSES = 30; // live signs kept for one utterance
export const UNRECOGNIZED_NOTICE_MS = 3000; // how long "not recognized" stays
export const PENDING_TIMEOUT_MS = 15000; // stop waiting for a sentence after this
export const UNCERTAIN_CONFIDENCE = 0.5; // below this a sign is shown as uncertain
