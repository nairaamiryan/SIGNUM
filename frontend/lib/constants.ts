export const ConnectionState = {
    IDLE: "idle",
    CONNECTING: "connecting",
    OPEN: "open",
    RECONNECTING: "reconnecting",
    CLOSED: "closed",
    FAILED: "failed",
} as const;

export const MAX_RECONNECT_ATTEMPTS = 3;
export const RECONNECT_BASE_DELAY_MS = 1000; // 1s, 2s, 4s backoff
export const RECONNECT_BACKOFF_MULTIPLIER = 2;