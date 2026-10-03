"use client";

import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import CameraFeed from "@/components/CameraFeed";
import CaptionDisplay from "@/components/CaptionDisplay";
import { useRecognitionSocket } from "@/lib/useRecognitionSocket";

export default function Home() {
  const { t } = useTranslation();

  const [caption, setCaption] = useState("");
  const [confidence, setConfidence] = useState<number | null>(null);
  const [unrecognized, setUnrecognized] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const { connect, disconnect, send } = useRecognitionSocket({
    onCaption: (text, conf) => {
      setCaption(text);
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
    setConfidence(null);
    setUnrecognized(false);
  }, [disconnect]);

  const handleFrameCaptured = useCallback(
    (canvas: HTMLCanvasElement) => {
      const data = canvas.toDataURL("image/jpeg", 0.6);
      send({ type: "frame", timestamp: Date.now(), data });
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
        onFrameCaptured={handleFrameCaptured}
        onFinalize={handleFinalize}
      />

      <CaptionDisplay
        caption={caption}
        confidence={confidence}
        unrecognized={unrecognized}
      />

      {connectionError && (
        <p className="text-red-500 text-sm max-w-2xl text-center">
          {connectionError}
        </p>
      )}
    </main>
  );
}