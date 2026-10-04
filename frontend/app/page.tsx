"use client";

import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import CameraFeed from "@/components/CameraFeed";
import CaptionDisplay from "@/components/CaptionDisplay";
import { useRecognitionSocket } from "@/lib/useRecognitionSocket";
import type { LandmarkFrame } from "@/lib/useHolisticLandmarks";

export default function Home() {
  const { t } = useTranslation();

  const [caption, setCaption] = useState("");
  const [gloss, setGloss] = useState<string[]>([]);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [unrecognized, setUnrecognized] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const { connect, disconnect, send, connectionState } = useRecognitionSocket({
    onCaption: (text, glossSequence, conf) => {
      setCaption(text);
      setGloss(glossSequence);
      setConfidence(conf);
      setUnrecognized(false);
    },
    onUnrecognized: () => {
      setUnrecognized(true);
    },
    onError: (message) => {
      setConnectionError(message);
    },
  });

  const handleStreamReady = useCallback(() => {
    setConnectionError(null);
    connect();
  }, [connect]);

  const handleStreamStopped = useCallback(() => {
    disconnect();
    setCaption("");
    setGloss([]);
    setConfidence(null);
    setUnrecognized(false);
  }, [disconnect]);

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
    [send]
  );

  const handleFinalize = useCallback(() => {
    send({ type: "finalize" });
  }, [send]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 gap-6">
      <h1 className="text-2xl font-bold">{t("app.title")}</h1>

      <CameraFeed
        onStreamReady={handleStreamReady}
        onStreamStopped={handleStreamStopped}
        onLandmarksDetected={handleLandmarksDetected}
        onFinalize={handleFinalize}
      />

      <CaptionDisplay
        caption={caption}
        gloss={gloss}
        confidence={confidence}
        unrecognized={unrecognized}
      />

      {connectionState === "reconnecting" && (
        <p className="text-amber-500 text-sm">{t("connection.reconnecting")}</p>
      )}

      {connectionError && (
        <p className="text-red-500 text-sm max-w-2xl text-center">
          {connectionError}
        </p>
      )}
    </main>
  );
}