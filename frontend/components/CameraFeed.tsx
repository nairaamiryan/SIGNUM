"use client";

import { useRef, useState, useCallback, useEffect } from "react";

export type RecognitionState = "idle" | "listening" | "processing" | "error";

interface CameraFeedProps {
  onStreamReady?: (stream: MediaStream) => void;
  onStreamStopped?: () => void;
  /** Called with each captured frame while listening — placeholder hook for
   * future MediaPipe landmark extraction / WebSocket transmission. */
  onFrameCaptured?: (canvas: HTMLCanvasElement) => void;
  /** Called when the user explicitly finalizes the current sentence. */
  onFinalize?: () => void;
}

const FRAME_CAPTURE_INTERVAL_MS = 100; // ~10 fps placeholder capture rate

export default function CameraFeed({
  onStreamReady,
  onStreamStopped,
  onFrameCaptured,
  onFinalize,
}: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const captureIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [state, setState] = useState<RecognitionState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const stopFrameCapture = useCallback(() => {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
  }, []);

  const startFrameCapture = useCallback(() => {
    stopFrameCapture();

    captureIntervalRef.current = setInterval(() => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.readyState < 2) return;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      // Placeholder: hand the captured frame off for landmark extraction /
      // WebSocket transmission once the Gesture Recognition Service is wired up.
      onFrameCaptured?.(canvas);
    }, FRAME_CAPTURE_INTERVAL_MS);
  }, [onFrameCaptured, stopFrameCapture]);

  const startCamera = useCallback(async () => {
    setErrorMessage(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: "user" },
        audio: false,
      });

      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setState("listening");
      onStreamReady?.(stream);
      startFrameCapture();
    } catch (err) {
      console.error("Camera access error:", err);
      setState("error");
      setErrorMessage(
        err instanceof Error ? err.message : "Unable to access camera"
      );
    }
  }, [onStreamReady, startFrameCapture]);

  const stopCamera = useCallback(() => {
    stopFrameCapture();

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    setState("idle");
    onStreamStopped?.();
  }, [onStreamStopped, stopFrameCapture]);

  const finalizeRecognition = useCallback(() => {
    if (state !== "listening") return;
    setState("processing");
    onFinalize?.();

    // Placeholder: once the Gesture Recognition Service responds with a
    // finished sentence, this should transition back to "listening" (or
    // "idle" if the camera was stopped). For now we just log it.
    console.log("Finalize requested — awaiting recognition service response.");
  }, [state, onFinalize]);

  // Clean up the interval and camera stream on unmount.
  useEffect(() => {
    return () => {
      stopFrameCapture();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [stopFrameCapture]);

  const stateLabel: Record<RecognitionState, string> = {
    idle: "Idle",
    listening: "● Listening",
    processing: "Processing...",
    error: "Error",
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
        {/* Hidden canvas used purely for frame capture, not displayed to the user. */}
        <canvas ref={canvasRef} className="hidden" />

        <div className="absolute top-2 left-2 px-3 py-1 rounded-full text-sm font-medium bg-black/60 text-white">
          {stateLabel[state]}
        </div>
      </div>

      {errorMessage && (
        <p className="text-red-500 text-sm">{errorMessage}</p>
      )}

      <div className="flex gap-3">
        {state === "idle" || state === "error" ? (
          <button
            onClick={startCamera}
            className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 transition"
          >
            Start Camera
          </button>
        ) : (
          <>
            <button
              onClick={finalizeRecognition}
              disabled={state !== "listening"}
              className="px-4 py-2 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Finalize
            </button>
            <button
              onClick={stopCamera}
              className="px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 transition"
            >
              Stop Camera
            </button>
          </>
        )}
      </div>
    </div>
  );
}