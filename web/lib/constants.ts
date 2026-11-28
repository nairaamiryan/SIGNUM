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

export const LifecyclePhase = {
    IDLE: "idle",
    READY: "ready",
    SIGNING: "signing",
    INACTIVE: "inactive",
    FINALIZING: "finalizing",
    TERMINATED: "terminated",
} as const;

export const MAX_RECONNECT_ATTEMPTS = 3;
export const RECONNECT_BASE_DELAY_MS = 1000; // 1s, 2s, 4s backoff
export const RECONNECT_BACKOFF_MULTIPLIER = 2;

export const ERROR_MESSAGES = {
    AUTH_REQUEST_FAILED: "Authentication request failed",
    GOOGLE_NOT_CONFIGURED: "Google sign-in is not configured",
    GOOGLE_AUTH_FAILED: "Google authentication failed",
    GOOGLE_EMAIL_NOT_VERIFIED: "Google account email is not verified",
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
    AMBIGUOUS: "ambiguous",
} as const;

export const CAPTION_HISTORY_LIMIT = 5; // completed captions kept on screen
export const MAX_PARTIAL_GLOSSES = 30; // live signs kept for one utterance
export const UNRECOGNIZED_NOTICE_MS = 3000; // how long "not recognized" stays
export const AMBIGUOUS_NOTICE_MS = 4000; // how long "ambiguous sign" stays
export const WARNING_NOTICE_MS = 4000; // how long an edge-case warning stays
export const LOW_LIGHT_LUMINANCE_THRESHOLD = 35; // 0-255 mean luminance below which lighting is poor
export const PENDING_TIMEOUT_MS = 15000; // stop waiting for a sentence after this
export const UNCERTAIN_CONFIDENCE = 0.5; // below this a sign is shown as uncertain

// --- Authentication and base UI ---
export const APP_NAME = "SIGNUM";
export const AUTH_STORAGE_KEY = "signum.auth";
export const LANGUAGE_STORAGE_KEY = "signum.language";
export const PASSWORD_MIN_LENGTH = 8;
export const NAME_MAX_LENGTH = 100;

export const Language = {
    HY_AM: "hy-AM",
    HY_WM: "hy-WM",
} as const;
export type Language = (typeof Language)[keyof typeof Language];
export const DEFAULT_LANGUAGE: Language = Language.HY_AM;

export const AuthProviderName = {
    LOCAL: "local",
    GOOGLE: "google",
} as const;

export const AppRoute = {
    HOME: "/",
    LOGIN: "/login",
    REGISTER: "/register",
} as const;

export const ApiRoute = {
    LOGIN: "/api/auth/login",
    REGISTER: "/api/auth/register",
    GOOGLE: "/api/auth/google",
    ME: "/api/users/me",
} as const;

export const HttpStatus = {
    BAD_REQUEST: 400,
    UNAUTHORIZED: 401,
    CONFLICT: 409,
    SERVICE_UNAVAILABLE: 503,
} as const;
