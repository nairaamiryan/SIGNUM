import { describe, expect, it } from "vitest";
import {
    captionFeedReducer as reduce,
    deriveRecognitionState as recognitionState,
    initialCaptionFeedState as initial,
} from "./captionFeed";
import type { CaptionFeedAction, CaptionFeedState } from "./captionFeed";
import type { ServerGlossSequenceMessage, ServerSentenceMessage } from "./types";

const run = (...actions: CaptionFeedAction[]): CaptionFeedState => actions.reduce(reduce, initial);

const token = (gloss: string, confidence: number) => ({
    gloss,
    confidence,
    startMs: 0,
    endMs: 1,
    status: "accepted" as const,
    repeats: 1,
});

const glossSequence = (
    utteranceId: number,
    glosses = [token("A", 0.9), token("B", 0.5)],
): ServerGlossSequenceMessage => ({
    type: "gloss_sequence",
    sessionId: "s",
    utteranceId,
    glosses,
    glossText: glosses.map((g) => g.gloss).join(" "),
    gaps: [],
    startMs: 0,
    endMs: 1,
    boundary: "pause",
});

const sentence = (
    utteranceId: number,
    text = "T",
    status: "ok" | "partial" | "fallback" = "ok",
    warnings: string[] = [],
): ServerSentenceMessage => ({
    type: "sentence",
    sessionId: "s",
    utteranceId,
    text,
    status,
    glossText: "A B",
    warnings,
    provider: "gemini",
    model: "m",
    latencyMs: 5,
});

describe("caption feed", () => {
    it("shows partial results immediately and replaces them with the sentence", () => {
        let state = run(
            { type: "server_state", state: "listening" },
            { type: "caption", gloss: ["A"], confidence: 0.9 },
            { type: "caption", gloss: ["B"], confidence: 0.5 },
        );
        expect(state.partials.map((p) => p.gloss)).toEqual(["A", "B"]);
        expect(recognitionState(state)).toBe("listening");

        state = reduce(state, { type: "gloss_sequence", message: glossSequence(1) });
        expect(state.partials).toHaveLength(0);
        expect(state.pending).toHaveLength(1);
        // Generating the sentence does not change the recognition state.
        expect(recognitionState(state)).toBe("listening");

        state = reduce(state, { type: "sentence", message: sentence(1, "Ես ջուր եմ ուզում։") });
        expect(state.pending).toHaveLength(0);
        expect(state.captions).toHaveLength(1);
        expect(state.captions[0].text).toBe("Ես ջուր եմ ուզում։");
        expect(state.captions[0].status).toBe("ok");
        expect(state.captions[0].glosses).toEqual(["A", "B"]);
        expect(state.captions[0].confidence).toBe(0.7);
    });

    it("adds one partial per gloss with unique ids", () => {
        const state = run({ type: "caption", gloss: ["A", "B", "C"], confidence: 0.75 });
        expect(new Set(state.partials.map((p) => p.id)).size).toBe(3);
    });

    it("caps the number of partial results", () => {
        let state = initial;
        for (let i = 0; i < 100; i++) {
            state = reduce(state, { type: "caption", gloss: ["A"], confidence: 0.9 });
        }
        expect(state.partials).toHaveLength(30);
    });

    it("uses glossText when a sentence arrives without a known gloss sequence", () => {
        const state = run({
            type: "sentence",
            message: sentence(7, "T", "partial", ["missing_glosses"]),
        });
        expect(state.captions[0].glosses).toEqual(["A", "B"]);
        expect(state.captions[0].confidence).toBeNull();
        expect(state.captions[0].status).toBe("partial");
        expect(state.captions[0].warnings).toEqual(["missing_glosses"]);
    });

    it("falls back to the signs when the sentence never arrives", () => {
        const state = run(
            { type: "gloss_sequence", message: glossSequence(1) },
            { type: "pending_timeout" },
        );
        expect(state.pending).toHaveLength(0);
        expect(state.captions[0].status).toBe("fallback");
        expect(state.captions[0].text).toBe("A B");
    });

    it("keeps a limited history, newest first, and replaces the same utterance", () => {
        let state = initial;
        for (let i = 1; i <= 8; i++) {
            state = reduce(state, { type: "sentence", message: sentence(i, `T${i}`) });
        }
        expect(state.captions.map((c) => c.id)).toEqual([8, 7, 6, 5, 4]);

        state = reduce(state, { type: "sentence", message: sentence(6, "T6-new") });
        expect(state.captions).toHaveLength(5);
        expect(state.captions[0].text).toBe("T6-new");
    });
});

describe("recognition state", () => {
    it("is Processing after finalize until the server is listening again", () => {
        let state = run(
            { type: "server_state", state: "listening" },
            { type: "finalize_requested" },
        );
        expect(recognitionState(state)).toBe("processing");

        state = reduce(state, { type: "server_state", state: "processing" });
        expect(recognitionState(state)).toBe("processing");

        state = reduce(state, { type: "server_state", state: "listening" });
        expect(recognitionState(state)).toBe("listening");
        expect(state.finalizing).toBe(false);
    });

    it("does not get stuck when finalize finds nothing to recognize", () => {
        const state = run(
            { type: "server_state", state: "listening" },
            { type: "finalize_requested" },
            { type: "unrecognized" },
        );
        expect(recognitionState(state)).toBe("listening");
        expect(state.unrecognized).toBe(true);
        expect(reduce(state, { type: "clear_unrecognized" }).unrecognized).toBe(false);
    });

    it("releases the finalize button on timeout", () => {
        const state = run(
            { type: "server_state", state: "listening" },
            { type: "finalize_requested" },
            { type: "finalize_timeout" },
        );
        expect(recognitionState(state)).toBe("listening");
    });

    it("shows errors and clears them when the server listens again or a caption arrives", () => {
        const failed = run(
            { type: "server_state", state: "listening" },
            { type: "error", message: "boom" },
        );
        expect(recognitionState(failed)).toBe("error");
        expect(failed.error).toBe("boom");

        const listening = reduce(failed, { type: "server_state", state: "listening" });
        expect(recognitionState(listening)).toBe("listening");

        const captioned = reduce(failed, { type: "caption", gloss: ["A"], confidence: 1 });
        expect(recognitionState(captioned)).toBe("listening");

        expect(recognitionState(run({ type: "server_state", state: "error" }))).toBe("error");
    });

    it("ends a pending finalize when an error arrives", () => {
        const state = run({ type: "finalize_requested" }, { type: "error", message: "x" });
        expect(state.finalizing).toBe(false);
    });

    it("clears the unrecognized notice on a caption and everything on reset", () => {
        let state = run({ type: "unrecognized" }, { type: "caption", gloss: ["A"], confidence: 1 });
        expect(state.unrecognized).toBe(false);

        state = run({ type: "sentence", message: sentence(1) }, { type: "reset" });
        expect(state).toEqual(initial);
    });
});
