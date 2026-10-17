"use client";

import { useRef, useCallback, useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import type {
    ClientMessage,
    ServerMessage,
    DistributiveOmit,
    UseRecognitionSocketOptions,
    ConnectionState as ConnectionStateType,
} from "./types";
import {
    ConnectionState,
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_BASE_DELAY_MS,
    RECONNECT_BACKOFF_MULTIPLIER,
} from "./constants";

function generateSessionId(): string {
    return typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function useRecognitionSocket({
    onCaption,
    onUnrecognized,
    onServerState,
    onError,
}: UseRecognitionSocketOptions) {
    const { t } = useTranslation();

    const socketRef = useRef<WebSocket | null>(null);
    const sessionIdRef = useRef<string | null>(null);
    const reconnectAttemptsRef = useRef(0);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const intentionalCloseRef = useRef(false);

    const [connectionState, setConnectionState] = useState<ConnectionStateType>(
        ConnectionState.IDLE
    );

    const clearReconnectTimeout = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
    }, []);

    const openSocket = useCallback(
        (isReconnect: boolean) => {
            const url = process.env.NEXT_PUBLIC_WS_URL;
            if (!url) {
                onError?.(t("connection.notConfigured"));
                setConnectionState(ConnectionState.FAILED);
                return;
            }

            setConnectionState(
                isReconnect ? ConnectionState.RECONNECTING : ConnectionState.CONNECTING
            );

            const socket = new WebSocket(url);
            socketRef.current = socket;

            socket.onopen = () => {
                reconnectAttemptsRef.current = 0;
                setConnectionState(ConnectionState.OPEN);

                if (sessionIdRef.current) {
                    socket.send(
                        JSON.stringify({ type: "connect", sessionId: sessionIdRef.current })
                    );
                }
            };

            socket.onclose = () => {
                if (intentionalCloseRef.current) {
                    setConnectionState(ConnectionState.CLOSED);
                    return;
                }

                // Unexpected close — attempt to reconnect with backoff.
                if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
                    const attempt = reconnectAttemptsRef.current + 1;
                    reconnectAttemptsRef.current = attempt;
                    const delay =
                        RECONNECT_BASE_DELAY_MS *
                        RECONNECT_BACKOFF_MULTIPLIER ** (attempt - 1);

                    setConnectionState(ConnectionState.RECONNECTING);
                    reconnectTimeoutRef.current = setTimeout(() => {
                        openSocket(true);
                    }, delay);
                } else {
                    setConnectionState(ConnectionState.FAILED);
                    onError?.(t("connection.error"));
                }
            };

            socket.onerror = () => {
                onError?.(t("connection.error"));
            };

            socket.onmessage = (event) => {
                try {
                    const message: ServerMessage = JSON.parse(event.data);

                    switch (message.type) {
                        case "caption":
                            onCaption?.(message.text, message.gloss, message.confidence);
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
                    console.warn(
                        "Received malformed message from Gesture Recognition Service:",
                        event.data
                    );
                }
            };
        },
        [onCaption, onUnrecognized, onServerState, onError, t]
    );

    const connect = useCallback(() => {
        clearReconnectTimeout();
        intentionalCloseRef.current = false;
        reconnectAttemptsRef.current = 0;
        sessionIdRef.current = generateSessionId();
        openSocket(false);
    }, [openSocket, clearReconnectTimeout]);

    const disconnect = useCallback(() => {
        intentionalCloseRef.current = true;
        clearReconnectTimeout();
        socketRef.current?.close();
        socketRef.current = null;
        sessionIdRef.current = null;
        setConnectionState(ConnectionState.IDLE);
    }, [clearReconnectTimeout]);

    const send = useCallback((message: DistributiveOmit<ClientMessage, "sessionId">) => {
        if (socketRef.current?.readyState === WebSocket.OPEN && sessionIdRef.current) {
            socketRef.current.send(
                JSON.stringify({ ...message, sessionId: sessionIdRef.current })
            );
        }
    }, []);

    // Ensure the socket and any pending reconnect are cleaned up on unmount.
    useEffect(() => {
        return () => {
            intentionalCloseRef.current = true;
            clearReconnectTimeout();
            socketRef.current?.close();
        };
    }, [clearReconnectTimeout]);

    return {
        connect,
        disconnect,
        send,
        connectionState,
        connected: connectionState === ConnectionState.OPEN,
    };
}