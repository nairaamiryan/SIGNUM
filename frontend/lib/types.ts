import type { LandmarkFrame } from "./useHolisticLandmarks";
import type { ConnectionState as ConnectionStateMap } from "./constants";

// Derived from the ConnectionState constant map in constants.ts.
export type ConnectionState =
    (typeof ConnectionStateMap)[keyof typeof ConnectionStateMap];

export type DistributiveOmit<T, K extends keyof T> = T extends unknown
    ? Omit<T, K>
    : never;

export type ServerState = "idle" | "listening" | "processing" | "error";

export interface UseRecognitionSocketOptions {
    onCaption?: (text: string, gloss: string[], confidence: number) => void;
    onUnrecognized?: () => void;
    onServerState?: (state: ServerState) => void;
    onError?: (message: string) => void;
}

// Messages sent from the client to the Gesture Recognition Service.
export interface ClientConnectMessage {
    type: "connect";
    sessionId: string;
}

export interface ClientLandmarksMessage {
    type: "landmarks";
    sessionId: string;
    timestamp: number;
    leftHand: LandmarkFrame["leftHand"];
    rightHand: LandmarkFrame["rightHand"];
    face: LandmarkFrame["face"];
    pose: LandmarkFrame["pose"];
}

export interface ClientFinalizeMessage {
    type: "finalize";
    sessionId: string;
}

export type ClientMessage =
    | ClientConnectMessage
    | ClientLandmarksMessage
    | ClientFinalizeMessage;

// Messages received from the Gesture Recognition Service.
export interface ServerCaptionMessage {
    type: "caption";
    text: string;
    gloss: string[];
    confidence: number;
}

export interface ServerStateMessage {
    type: "state";
    state: ServerState;
}

export interface ServerUnrecognizedMessage {
    type: "unrecognized";
}

export interface ServerErrorMessage {
    type: "error";
    message: string;
}

export type ServerMessage =
    | ServerCaptionMessage
    | ServerStateMessage
    | ServerUnrecognizedMessage
    | ServerErrorMessage;