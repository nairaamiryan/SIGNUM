"use client";

import { useRef, useCallback, useState } from "react";
import {
    FilesetResolver,
    HolisticLandmarker,
    type HolisticLandmarkerResult,
} from "@mediapipe/tasks-vision";

export interface LandmarkFrame {
    timestamp: number;
    /** 21 points per hand, normalized (x, y, z). Null if the hand is not visible. */
    leftHand: Array<{ x: number; y: number; z: number }> | null;
    rightHand: Array<{ x: number; y: number; z: number }> | null;
    /** Subset of face landmarks relevant to non-manual grammatical markers. */
    face: Array<{ x: number; y: number; z: number }> | null;
    /** Upper-body pose landmarks. */
    pose: Array<{ x: number; y: number; z: number }> | null;
}

const MODEL_ASSET_PATH =
    "https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task";

const WASM_BASE_PATH =
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm";

export function useHolisticLandmarks() {
    const landmarkerRef = useRef<HolisticLandmarker | null>(null);
    const [isReady, setIsReady] = useState(false);
    const [loadError, setLoadError] = useState<string | null>(null);

    const initialize = useCallback(async () => {
        if (landmarkerRef.current) return;

        try {
            const vision = await FilesetResolver.forVisionTasks(WASM_BASE_PATH);
            landmarkerRef.current = await HolisticLandmarker.createFromOptions(vision, {
                baseOptions: {
                    modelAssetPath: MODEL_ASSET_PATH,
                    delegate: "GPU",
                },
                runningMode: "VIDEO",
            });
            setIsReady(true);
        } catch (err) {
            console.error("Failed to initialize MediaPipe Holistic:", err);
            setLoadError(
                err instanceof Error ? err.message : "Failed to load landmark model"
            );
        }
    }, []);

    const detectFrame = useCallback(
        (video: HTMLVideoElement, timestampMs: number): LandmarkFrame | null => {
            const landmarker = landmarkerRef.current;
            if (!landmarker || video.readyState < 2) return null;

            let result: HolisticLandmarkerResult;
            try {
                result = landmarker.detectForVideo(video, timestampMs);
            } catch (err) {
                console.error("Landmark detection error:", err);
                return null;
            }

            return {
                timestamp: timestampMs,
                leftHand: result.leftHandLandmarks?.[0]?.map((p) => ({ x: p.x, y: p.y, z: p.z })) ?? null,
                rightHand: result.rightHandLandmarks?.[0]?.map((p) => ({ x: p.x, y: p.y, z: p.z })) ?? null,
                face: result.faceLandmarks?.[0]?.map((p) => ({ x: p.x, y: p.y, z: p.z })) ?? null,
                pose: result.poseLandmarks?.[0]?.map((p) => ({ x: p.x, y: p.y, z: p.z })) ?? null,
            };
        },
        []
    );

    const close = useCallback(() => {
        landmarkerRef.current?.close();
        landmarkerRef.current = null;
        setIsReady(false);
    }, []);

    return { initialize, detectFrame, close, isReady, loadError };
}