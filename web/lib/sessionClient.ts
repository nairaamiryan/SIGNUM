import { ApiRoute } from "./constants";

/**
 * Create a persisted recognition session in PostgreSQL for an authenticated user.
 * Returns the database session ID, or null if creation fails (so recognition can
 * still proceed with an ephemeral client-generated session ID).
 */
export async function createRecognitionSession(token: string): Promise<string | null> {
    try {
        const res = await fetch(ApiRoute.SESSIONS, {
            method: "POST",
            headers: {
                Authorization: `Bearer ${token}`,
            },
        });
        if (!res.ok) return null;
        const data = (await res.json()) as { id?: unknown };
        return typeof data.id === "string" && data.id ? data.id : null;
    } catch {
        return null;
    }
}

/**
 * Mark a persisted recognition session as ended in PostgreSQL.
 * Uses keepalive so the request still completes when the tab closes.
 */
export async function endRecognitionSession(sessionId: string, token: string): Promise<void> {
    try {
        await fetch(`${ApiRoute.SESSIONS}/${encodeURIComponent(sessionId)}`, {
            method: "PATCH",
            headers: {
                Authorization: `Bearer ${token}`,
            },
            keepalive: true,
        });
    } catch {
        // Non-blocking cleanup: do not disrupt camera stop or page unload.
    }
}
