"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { Camera, CameraOff, CheckCheck, RotateCcw, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LOW_LIGHT_LUMINANCE_THRESHOLD } from "@/lib/constants";
import { useHolisticLandmarks, type LandmarkFrame } from "@/lib/useHolisticLandmarks";
import type { LifecyclePhase, ServerState } from "@/lib/types";

export type RecognitionState = "idle" | "listening" | "processing" | "error";

interface CameraFeedProps {
    onStreamReady?: (stream: MediaStream) => void;
    onStreamStopped?: () => void;
    /** Called with each detected landmark frame while listening. */
    onLandmarksDetected?: (frame: LandmarkFrame) => void;
    /** Called when the user explicitly finalizes the current sentence. */
    onFinalize?: () => void;
    /** Called when the user requests re-evaluation of the last sign. */
    onRepeat?: () => void;
    /** Called when the user restarts the current sentence. */
    onRestart?: () => void;
    /**
     * Recognition state reported by the page from the server events. While the
     * camera is on it decides the badge and whether Finalize is enabled.
     */
    status?: ServerState;
    /** Shared signing-sequence lifecycle phase from the recognition pipeline (KAN-26). */
    lifecyclePhase?: LifecyclePhase;
}

const DETECTION_INTERVAL_MS = 100; // ~10 fps
const LUMINANCE_CHECK_EVERY_N_FRAMES = 10;

function sampleVideoLuminance(video: HTMLVideoElement, canvas: HTMLCanvasElement): number | null {
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx || video.videoWidth === 0 || video.videoHeight === 0) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
    let sum = 0;
    const pixels = data.length / 4;
    for (let i = 0; i < data.length; i += 4) {
        sum += 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
    }
    return pixels > 0 ? sum / pixels : null;
}

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
    onRepeat,
    onRestart,
    status,
    lifecyclePhase,
}: CameraFeedProps) {
    const { t } = useTranslation();
    const { initialize, detectFrame, close, loadError } = useHolisticLandmarks();

    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const detectionIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const lumCanvasRef = useRef<HTMLCanvasElement | null>(null);
    const frameCounterRef = useRef(0);
    const poorIlluminationRef = useRef(false);

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

            frameCounterRef.current += 1;
            if (frameCounterRef.current % LUMINANCE_CHECK_EVERY_N_FRAMES === 0) {
                if (!lumCanvasRef.current) {
                    const c = document.createElement("canvas");
                    c.width = 32;
                    c.height = 18;
                    lumCanvasRef.current = c;
                }
                const lum = sampleVideoLuminance(video, lumCanvasRef.current);
                poorIlluminationRef.current = lum !== null && lum < LOW_LIGHT_LUMINANCE_THRESHOLD;
            }

            const frame = detectFrame(video, performance.now());
            if (frame) {
                onLandmarksDetected?.({
                    ...frame,
                    poorIllumination: poorIlluminationRef.current,
                });
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

            // Detect unexpected hardware/permission camera disconnection.
            for (const track of stream.getVideoTracks()) {
                track.onended = () => {
                    stopDetection();
                    streamRef.current = null;
                    if (videoRef.current) {
                        videoRef.current.srcObject = null;
                    }
                    setState("error");
                    setErrorMessage(t("camera.disconnected"));
                    onStreamStopped?.();
                };
            }

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

    const lifecycleLabel: Record<LifecyclePhase, string> = {
        idle: t("lifecycle.idle"),
        ready: t("lifecycle.ready"),
        signing: t("lifecycle.signing"),
        inactive: t("lifecycle.inactive"),
        finalizing: t("lifecycle.finalizing"),
        terminated: t("lifecycle.terminated"),
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

                {displayState !== "idle" && lifecyclePhase && (
                    <Badge
                        variant="secondary"
                        className="absolute top-3 right-3 bg-black/60 px-3 py-1 text-xs text-white"
                    >
                        {lifecycleLabel[lifecyclePhase]}
                    </Badge>
                )}
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
                        {onRepeat && (
                            <Button
                                variant="outline"
                                onClick={onRepeat}
                                disabled={displayState !== "listening"}
                            >
                                <RotateCcw />
                                {t("controls.repeat")}
                            </Button>
                        )}
                        {onRestart && (
                            <Button
                                variant="outline"
                                onClick={onRestart}
                                disabled={displayState !== "listening"}
                            >
                                <RefreshCw />
                                {t("controls.restart")}
                            </Button>
                        )}
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
