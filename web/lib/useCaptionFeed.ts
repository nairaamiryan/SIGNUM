"use client";

import { useCallback, useEffect, useReducer } from "react";
import { captionFeedReducer, deriveRecognitionState, initialCaptionFeedState } from "./captionFeed";
import { PENDING_TIMEOUT_MS, UNRECOGNIZED_NOTICE_MS } from "./constants";
import type { ServerGlossSequenceMessage, ServerSentenceMessage, ServerState } from "./types";

/**
 * Real-time captioning state (KAN-23): partial results, completed sentences,
 * confidence, the recognition state and errors, driven by the events of the
 * Gesture Recognition Service.
 *
 * Every handler is stable (it only dispatches), so it is safe to pass them to
 * useRecognitionSocket: the WebSocket keeps the handlers it was opened with.
 */
export function useCaptionFeed() {
    const [state, dispatch] = useReducer(captionFeedReducer, initialCaptionFeedState);

    const onCaption = useCallback(
        (_text: string, gloss: string[], confidence: number) =>
            dispatch({ type: "caption", gloss, confidence }),
        [],
    );
    const onUnrecognized = useCallback(() => dispatch({ type: "unrecognized" }), []);
    const onServerState = useCallback(
        (serverState: ServerState) => dispatch({ type: "server_state", state: serverState }),
        [],
    );
    const onGlossSequence = useCallback(
        (message: ServerGlossSequenceMessage) => dispatch({ type: "gloss_sequence", message }),
        [],
    );
    const onSentence = useCallback(
        (message: ServerSentenceMessage) => dispatch({ type: "sentence", message }),
        [],
    );
    const onError = useCallback((message: string) => dispatch({ type: "error", message }), []);
    const onFinalizeRequested = useCallback(() => dispatch({ type: "finalize_requested" }), []);
    const reset = useCallback(() => dispatch({ type: "reset" }), []);

    // The "gesture not recognized" notice disappears by itself.
    useEffect(() => {
        if (!state.unrecognized) return;
        const timer = setTimeout(
            () => dispatch({ type: "clear_unrecognized" }),
            UNRECOGNIZED_NOTICE_MS,
        );
        return () => clearTimeout(timer);
    }, [state.unrecognized]);

    // Never wait forever for a sentence that does not come.
    const pendingCount = state.pending.length;
    useEffect(() => {
        if (pendingCount === 0) return;
        const timer = setTimeout(() => dispatch({ type: "pending_timeout" }), PENDING_TIMEOUT_MS);
        return () => clearTimeout(timer);
    }, [pendingCount]);

    // Or for the answer to a finalize request.
    useEffect(() => {
        if (!state.finalizing) return;
        const timer = setTimeout(() => dispatch({ type: "finalize_timeout" }), PENDING_TIMEOUT_MS);
        return () => clearTimeout(timer);
    }, [state.finalizing]);

    return {
        status: deriveRecognitionState(state),
        partials: state.partials,
        captions: state.captions,
        /** A sentence is being generated for an utterance that has ended. */
        generating: pendingCount > 0,
        unrecognized: state.unrecognized,
        error: state.error,
        onCaption,
        onUnrecognized,
        onServerState,
        onGlossSequence,
        onSentence,
        onError,
        onFinalizeRequested,
        reset,
    };
}
