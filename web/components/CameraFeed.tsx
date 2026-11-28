"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { Camera, CameraOff, CheckCheck } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useHolisticLandmarks, type LandmarkFrame } from "@/lib/useHolisticLandmarks";
import type { ServerState } from "@/lib/types";

export type RecognitionState = "idle" | "listening" | "processing" | "error";

interface CameraFeedProps {
    onStreamReady?: (stream: MediaStream) => void;
    onStreamStopped?: () => void;
    /** Called with each detected landmark frame while listening. */
    onLandmarksDetected?: (frame: LandmarkFrame) => void;
    /** Called when the user explicitly finalizes the current sentence. */
    onFinalize?: () => void;
    /**
     * Recognition state reported by the page from the server events. While the
     * camera is on it decides the badge and whether Finalize is enabled.
     */
    status?: ServerState;
}

const DETECTION_INTERVAL_MS = 100; // ~10 fps

const STATE_BADGE_CLASS: Record<RecognitionState, string> = {
    idle: "bg-black/60 text-white",
    listening: "bg-emerald-600/90 text-white",
    processing: "bg-amber-500/95 text-black",
    error: "bg-red-600/90 text-white",
};

export default function CameraFeed({
    onStreamReady,
    onStreamStopped,
    onLandmarksDetected,
    onFinalize,
    status,
}: CameraFeedProps) {
    const { t } = useTranslation();
    const { initialize, detectFrame, close, loadError } = useHolisticLandmarks();

    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const detectionIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const [state, setState] = useState<RecognitionState>("idle");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [modelLoading, setModelLoading] = useState(false);

    const stopDetection = useCallback(() => {
        if (detectionIntervalRef.current) {
            clearInterval(detectionIntervalRef.current);
            detectionIntervalRef.current = null;
        }
    }, []);

    const startDetection = useCallback(() => {
        stopDetection();

        detectionIntervalRef.current = setInterval(() => {
            const video = videoRef.current;
            if (!video) return;

            const frame = detectFrame(video, performance.now());
            if (frame) {
                onLandmarksDetected?.(frame);
            }
        }, DETECTION_INTERVAL_MS);
    }, [detectFrame, onLandmarksDetected, stopDetection]);

    const startCamera = useCallback(async () => {
        setErrorMessage(null);
        setModelLoading(true);

        try {
            await initialize();

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 1280, height: 720, facingMode: "user" },
                audio: false,
            });

            streamRef.current = stream;

            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play();
            }

            setModelLoading(false);
            setState("listening");
            onStreamReady?.(stream);
            startDetection();
        } catch (err) {
            console.error("Camera/model initialization error:", err);
            setModelLoading(false);
            setState("error");
            setErrorMessage(err instanceof Error ? err.message : t("camera.accessError"));
        }
    }, [initialize, onStreamReady, startDetection, t]);

    const stopCamera = useCallback(() => {
        stopDetection();

        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }

        setState("idle");
        onStreamStopped?.();
    }, [onStreamStopped, stopDetection]);

    // While the camera is on, the recognition state comes from the server events.
    const displayState: RecognitionState =
        state === "idle" || state === "error" ? state : (status ?? state);

    const finalizeRecognition = useCallback(() => {
        if (displayState !== "listening") return;
        onFinalize?.();
    }, [displayState, onFinalize]);

    // Clean up on unmount.
    useEffect(() => {
        return () => {
            stopDetection();
            streamRef.current?.getTracks().forEach((track) => track.stop());
            close();
        };
    }, [stopDetection, close]);

    const stateLabel: Record<RecognitionState, string> = {
        idle: t("state.idle"),
        listening: t("state.listening"),
        processing: t("state.processing"),
        error: t("state.error"),
    };

    return (
        <div className="flex flex-col gap-4">
            <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-black">
                <video ref={videoRef} className="h-full w-full object-cover" muted playsInline />

                <Badge
                    role="status"
                    aria-live="polite"
                    className={`absolute top-3 left-3 border-transparent px-3 py-1 text-sm ${STATE_BADGE_CLASS[modelLoading ? "processing" : displayState]}`}
                >
                    {modelLoading ? t("state.processing") : stateLabel[displayState]}
                </Badge>
            </div>

            {(errorMessage || loadError) && (
                <Alert variant="destructive">
                    <AlertDescription>{errorMessage || loadError}</AlertDescription>
                </Alert>
            )}

            <div className="flex flex-wrap gap-3">
                {state === "idle" || state === "error" ? (
                    <Button onClick={startCamera} disabled={modelLoading}>
                        <Camera />
                        {t("controls.startCamera")}
                    </Button>
                ) : (
                    <>
                        <Button
                            variant="success"
                            onClick={finalizeRecognition}
                            disabled={displayState !== "listening"}
                        >
                            <CheckCheck />
                            {t("controls.finalize")}
                        </Button>
                        <Button variant="destructive" onClick={stopCamera}>
                            <CameraOff />
                            {t("controls.stopCamera")}
                        </Button>
                    </>
                )}
            </div>
        </div>
    );
}
