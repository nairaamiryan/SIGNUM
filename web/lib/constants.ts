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
