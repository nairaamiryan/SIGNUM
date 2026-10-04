"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useHolisticLandmarks, type LandmarkFrame } from "@/lib/useHolisticLandmarks";

export type RecognitionState = "idle" | "listening" | "processing" | "error";

interface CameraFeedProps {
  onStreamReady?: (stream: MediaStream) => void;
  onStreamStopped?: () => void;
  /** Called with each detected landmark frame while listening. */
  onLandmarksDetected?: (frame: LandmarkFrame) => void;
  /** Called when the user explicitly finalizes the current sentence. */
  onFinalize?: () => void;
}

const DETECTION_INTERVAL_MS = 100; // ~10 fps

export default function CameraFeed({
  onStreamReady,
  onStreamStopped,
  onLandmarksDetected,
  onFinalize,
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
      setErrorMessage(
        err instanceof Error ? err.message : t("camera.accessError")
      );
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

  const finalizeRecognition = useCallback(() => {
    if (state !== "listening") return;
    setState("processing");
    onFinalize?.();
  }, [state, onFinalize]);

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
    <div className="flex flex-col items-center gap-4">
      <div className="relative w-full max-w-2xl aspect-video bg-black rounded-lg overflow-hidden">
        <video
          ref={videoRef}
          className="w-full h-full object-cover"
          muted
          playsInline
        />

        <div className="absolute top-2 left-2 px-3 py-1 rounded-full text-sm font-medium bg-black/60 text-white">
          {modelLoading ? t("state.processing") : stateLabel[state]}
        </div>
      </div>

      {(errorMessage || loadError) && (
        <p className="text-red-500 text-sm">{errorMessage || loadError}</p>
      )}

      <div className="flex gap-3">
        {state === "idle" || state === "error" ? (
          <button
            onClick={startCamera}
            disabled={modelLoading}
            className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {t("controls.startCamera")}
          </button>
        ) : (
          <>
            <button
              onClick={finalizeRecognition}
              disabled={state !== "listening"}
              className="px-4 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t("controls.finalize")}
            </button>
            <button
              onClick={stopCamera}
              className="px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 transition"
            >
              {t("controls.stopCamera")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}