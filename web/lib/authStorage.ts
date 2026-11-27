import { AUTH_STORAGE_KEY } from "./constants";
import type { AuthSession } from "./types";

// The signed-in session is kept in localStorage and exposed to React as an
// external store (see AuthProvider), so every tab stays in sync.
const listeners = new Set<() => void>();

function emit(): void {
    listeners.forEach((listener) => listener());
}

export function readRawSession(): string | null {
    try {
        return localStorage.getItem(AUTH_STORAGE_KEY);
    } catch {
        return null;
    }
}

export function parseSession(raw: string | null): AuthSession | null {
    if (!raw) return null;
    try {
        const data: unknown = JSON.parse(raw);
        if (typeof data !== "object" || data === null) return null;
        const { token, user } = data as Partial<AuthSession>;
        if (typeof token !== "string" || !token) return null;
        if (!user || typeof user.id !== "string" || typeof user.email !== "string") return null;
        return {
            token,
            user: {
                id: user.id,
                email: user.email,
                name: typeof user.name === "string" ? user.name : null,
                avatarUrl: typeof user.avatarUrl === "string" ? user.avatarUrl : null,
            },
        };
    } catch {
        return null;
    }
}

export function saveSession(session: AuthSession): void {
    try {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
    } catch {
        // Storage can be unavailable (private mode); the user then stays signed out.
    }
    emit();
}

export function clearSession(): void {
    try {
        localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch {
        // See saveSession.
    }
    emit();
}

export function subscribeSession(listener: () => void): () => void {
    listeners.add(listener);
    // "storage" fires when another tab changes the session.
    window.addEventListener("storage", listener);
    return () => {
        listeners.delete(listener);
        window.removeEventListener("storage", listener);
    };
}
