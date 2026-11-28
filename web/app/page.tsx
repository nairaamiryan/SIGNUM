"use client";

import { useCallback } from "react";
import { TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import CameraFeed from "@/components/CameraFeed";
import CaptionDisplay from "@/components/CaptionDisplay";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
        onLifecycle: feed.onLifecycle,
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

    const { onFinalizeRequested, onRestartRequested } = feed;

    const handleFinalize = useCallback(() => {
        onFinalizeRequested();
        send({ type: "finalize" });
    }, [onFinalizeRequested, send]);

    const handleRepeat = useCallback(() => {
        send({ type: "repeat" });
    }, [send]);

    const handleRestart = useCallback(() => {
        onRestartRequested();
        send({ type: "restart" });
    }, [onRestartRequested, send]);

    return (
        <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8">
            <section className="flex flex-col gap-2 text-center">
                <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{t("app.title")}</h1>
                <p className="mx-auto max-w-2xl text-muted-foreground">{t("home.description")}</p>
            </section>

            {connectionState === ConnectionState.RECONNECTING && (
                <Alert variant="warning" role="status">
                    <TriangleAlert />
                    <AlertDescription>{t("connection.reconnecting")}</AlertDescription>
                </Alert>
            )}

            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
                <Card>
                    <CardHeader>
                        <CardTitle>{t("home.cameraTitle")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <CameraFeed
                            status={status}
                            lifecyclePhase={feed.lifecyclePhase}
                            onStreamReady={handleStreamReady}
                            onStreamStopped={handleStreamStopped}
                            onLandmarksDetected={handleLandmarksDetected}
                            onFinalize={handleFinalize}
                            onRepeat={handleRepeat}
                            onRestart={handleRestart}
                        />
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>{t("home.captionsTitle")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <CaptionDisplay
                            partials={feed.partials}
                            captions={feed.captions}
                            generating={feed.generating}
                            unrecognized={feed.unrecognized}
                            ambiguous={feed.ambiguous}
                            ambiguousCandidates={feed.ambiguousCandidates}
                            error={feed.error}
                        />
                    </CardContent>
                </Card>
            </div>
        </main>
    );
}
