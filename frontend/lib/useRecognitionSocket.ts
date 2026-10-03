"use client";

import { useRef, useCallback, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import type { ClientMessage, ServerMessage } from "./types";

interface UseRecognitionSocketOptions {
    onCaption?: (text: string, confidence: number) => void;
    onUnrecognized?: () => void;
    onServerState?: (state: "idle" | "listening" | "processing" | "error") => void;
    onError?: (message: string) => void;
}

export function useRecognitionSocket({
    onCaption,
    onUnrecognized,
    onServerState,
    onError,
}: UseRecognitionSocketOptions) {
    const { t } = useTranslation();

    const socketRef = useRef<WebSocket | null>(null);
    const [connected, setConnected] = useState(false);

    const connect = useCallback(() => {
        const url = process.env.NEXT_PUBLIC_WS_URL;
        if (!url) {
            onError?.(t("connection.notConfigured"));
            return;
        }

        const socket = new WebSocket(url);
        socketRef.current = socket;

        socket.onopen = () => setConnected(true);

        socket.onclose = () => setConnected(false);

        socket.onerror = () => {
            onError?.(t("connection.error"));
        };

        socket.onmessage = (event) => {
            try {
                const message: ServerMessage = JSON.parse(event.data);

                switch (message.type) {
                    case "caption":
                        onCaption?.(message.text, message.confidence);
                        break;
                    case "unrecognized":
                        onUnrecognized?.();
                        break;
                    case "state":
                        onServerState?.(message.state);
                        break;
                    case "error":
                        onError?.(message.message);
                        break;
                }
            } catch {
                console.warn("Received malformed message from Gesture Recognition Service:", event.data);
            }
        };
    }, [onCaption, onUnrecognized, onServerState, onError, t]);

    const disconnect = useCallback(() => {
        socketRef.current?.close();
        socketRef.current = null;
        setConnected(false);
    }, []);

    const send = useCallback((message: ClientMessage) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify(message));
        }
    }, []);

    // Ensure the socket is closed if the component unmounts unexpectedly.
    useEffect(() => {
        return () => {
            socketRef.current?.close();
        };
    }, []);

    return { connect, disconnect, send, connected };
}