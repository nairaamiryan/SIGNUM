"use client";

import { useCallback } from "react";
import { useTranslation } from "react-i18next";
import CameraFeed from "@/components/CameraFeed";
import CaptionDisplay from "@/components/CaptionDisplay";
import { useCaptionFeed } from "@/lib/useCaptionFeed";
import { useRecognitionSocket } from "@/lib/useRecognitionSocket";
import { ConnectionState, ServerState } from "@/lib/constants";
import type { LandmarkFrame } from "@/lib/useHolisticLandmarks";

export default function Home() {
    const { t } = useTranslation();

    // Partial results, completed sentences, confidence, state and errors,
    // driven by the events of the recognition and NLP pipeline.
    const feed = useCaptionFeed();

    const { connect, disconnect, send, connectionState } = useRecognitionSocket({
        onCaption: feed.onCaption,
        onUnrecognized: feed.onUnrecognized,
        onServerState: feed.onServerState,
        onGlossSequence: feed.onGlossSequence,
        onSentence: feed.onSentence,
        onError: feed.onError,
    });

    // Without an open connection the server cannot be listening.
    const status =
        connectionState === ConnectionState.OPEN || feed.status === ServerState.ERROR
            ? feed.status
            : ServerState.IDLE;

    const { reset } = feed;

    const handleStreamReady = useCallback(() => {
        reset();
        connect();
    }, [reset, connect]);

    const handleStreamStopped = useCallback(() => {
        disconnect();
        reset();
    }, [disconnect, reset]);

    const handleLandmarksDetected = useCallback(
        (frame: LandmarkFrame) => {
            send({
                type: "landmarks",
                timestamp: frame.timestamp,
                leftHand: frame.leftHand,
                rightHand: frame.rightHand,
                face: frame.face,
                pose: frame.pose,
            });
        },
        [send],
    );

    const { onFinalizeRequested } = feed;

    const handleFinalize = useCallback(() => {
        onFinalizeRequested();
        send({ type: "finalize" });
    }, [onFinalizeRequested, send]);

    return (
        <main className="min-h-screen flex flex-col items-center justify-center p-8 gap-6">
            <h1 className="text-2xl font-bold">{t("app.title")}</h1>

            <CameraFeed
                status={status}
                onStreamReady={handleStreamReady}
                onStreamStopped={handleStreamStopped}
                onLandmarksDetected={handleLandmarksDetected}
                onFinalize={handleFinalize}
            />

            {connectionState === ConnectionState.RECONNECTING && (
                <p role="status" className="text-amber-500 text-sm">
                    {t("connection.reconnecting")}
                </p>
            )}

            <CaptionDisplay
                partials={feed.partials}
                captions={feed.captions}
                generating={feed.generating}
                unrecognized={feed.unrecognized}
                error={feed.error}
            />
        </main>
    );
}
