"use client";

import { useRef, useState, useCallback } from "react";

export type CameraState = "idle" | "listening" | "processing" | "error";

interface CameraFeedProps {
    onStreamReady?: (stream: MediaStream) => void;
    onStreamStopped?: () => void;
}

export default function CameraFeed({ onStreamReady, onStreamStopped }: CameraFeedProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const streamRef = useRef<MediaStream | null>(null);

    const [state, setState] = useState<CameraState>("idle");
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
        } catch (err) {
            console.error("Camera access error:", err);
            setState("error");
            setErrorMessage(
                err instanceof Error ? err.message : "Unable to access camera"
            );
        }
    }, [onStreamReady]);

    const stopCamera = useCallback(() => {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (videoRef.current) {
            videoRef.current.srcObject = null;
        }

        setState("idle");
        onStreamStopped?.();
    }, [onStreamStopped]);

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
                    {state === "idle" && "Idle"}
                    {state === "listening" && "● Listening"}
                    {state === "processing" && "Processing..."}
                    {state === "error" && "Error"}
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
                    <button
                        onClick={stopCamera}
                        className="px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700 transition"
                    >
                        Stop Camera
                    </button>
                )}
            </div>
        </div>
    );
}