import { afterEach, describe, expect, it, vi } from "vitest";
import {
    captionFeedReducer as reduce,
    deriveRecognitionState as recognitionState,
    initialCaptionFeedState as initial,
} from "./captionFeed";
import { createRecognitionSession, endRecognitionSession } from "./sessionClient";
import { ApiRoute } from "./constants";

describe("end-to-end frontend integration", () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it("creates and ends a PostgreSQL recognition session via Next.js API", async () => {
        const fetchMock = vi
            .fn()
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ id: "pg-session-123" }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ ok: true }),
            });
        vi.stubGlobal("fetch", fetchMock);

        const sessionId = await createRecognitionSession("jwt-token");
        expect(sessionId).toBe("pg-session-123");
        expect(fetchMock).toHaveBeenNthCalledWith(1, ApiRoute.SESSIONS, {
            method: "POST",
            headers: { Authorization: "Bearer jwt-token" },
        });

        await endRecognitionSession("pg-session-123", "jwt-token");
        expect(fetchMock).toHaveBeenNthCalledWith(2, `${ApiRoute.SESSIONS}/pg-session-123`, {
            method: "PATCH",
            headers: { Authorization: "Bearer jwt-token" },
            keepalive: true,
        });
    });

    it("falls back to null when session creation fails so recognition continues", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValueOnce({
                ok: false,
                status: 500,
            }),
        );

        const sessionId = await createRecognitionSession("jwt-token");
        expect(sessionId).toBeNull();
    });

    it("processes full pipeline events from connect to Armenian sentence and restart", () => {
        let state = reduce(initial, { type: "server_state", state: "listening" });
        state = reduce(state, {
            type: "lifecycle",
            message: {
                type: "lifecycle",
                sessionId: "pg-session-123",
                phase: "signing",
                reason: "active_signing",
                signerPresent: true,
                signerPositioned: true,
                inactivityMs: 0,
            },
        });
        expect(recognitionState(state)).toBe("listening");
        expect(state.lifecyclePhase).toBe("signing");

        // Partial preview during active gesture
        state = reduce(state, {
            type: "partial_caption",
            gloss: ["ԲԱՐԵՒ"],
            confidence: 0.72,
        });
        expect(state.preview?.gloss).toBe("ԲԱՐԵՒ");

        // Final gesture classification supersedes preview
        state = reduce(state, {
            type: "caption",
            gloss: ["ԲԱՐԵՒ"],
            confidence: 0.91,
        });
        expect(state.preview).toBeNull();
        expect(state.partials).toHaveLength(1);

        // Gloss sequence + Armenian sentence
        state = reduce(state, {
            type: "gloss_sequence",
            message: {
                type: "gloss_sequence",
                sessionId: "pg-session-123",
                utteranceId: 1,
                glosses: [
                    {
                        gloss: "ԲԱՐԵՒ",
                        confidence: 0.91,
                        startMs: 0,
                        endMs: 500,
                        status: "accepted",
                        repeats: 1,
                    },
                ],
                glossText: "ԲԱՐԵՒ",
                gaps: [],
                startMs: 0,
                endMs: 500,
                boundary: "finalize",
            },
        });
        expect(state.partials).toHaveLength(0);
        expect(state.pending).toHaveLength(1);

        state = reduce(state, {
            type: "sentence",
            message: {
                type: "sentence",
                sessionId: "pg-session-123",
                utteranceId: 1,
                text: "Բարև ձեզ։",
                status: "ok",
                glossText: "ԲԱՐԵՒ",
                warnings: [],
                provider: "gemini",
                model: "gemini-3.5-flash-lite",
                latencyMs: 15,
            },
        });
        expect(state.pending).toHaveLength(0);
        expect(state.captions[0].text).toBe("Բարև ձեզ։");
        expect(state.captions[0].status).toBe("ok");

        // Restart terminates current utterance cleanly
        state = reduce(state, { type: "restart" });
        expect(state.lifecyclePhase).toBe("terminated");
        expect(state.partials).toEqual([]);
    });
});
