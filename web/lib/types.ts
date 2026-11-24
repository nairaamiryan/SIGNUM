import type { LandmarkFrame } from "./useHolisticLandmarks";
import type {
    ConnectionState as ConnectionStateMap,
    GlossStatus as GlossStatusMap,
    SentenceStatus as SentenceStatusMap,
    ServerState as ServerStateMap,
} from "./constants";

// Derived from the ConnectionState constant map in constants.ts.
export type ConnectionState =
    (typeof ConnectionStateMap)[keyof typeof ConnectionStateMap];

// Derived from the ServerState constant map in constants.ts.
export type ServerState =
    (typeof ServerStateMap)[keyof typeof ServerStateMap];

// Status of a generated sentence (NLP layer), from the SentenceStatus constant map.
export type SentenceStatus =
    (typeof SentenceStatusMap)[keyof typeof SentenceStatusMap];

// Confidence class of one recognized sign, from the GlossStatus constant map.
export type GlossStatus =
    (typeof GlossStatusMap)[keyof typeof GlossStatusMap];

export type DistributiveOmit<T, K extends keyof T> = T extends unknown
    ? Omit<T, K>
    : never;

export interface UseRecognitionSocketOptions {
    onCaption?: (text: string, gloss: string[], confidence: number) => void;
    onUnrecognized?: () => void;
    onServerState?: (state: ServerState) => void;
    onGlossSequence?: (message: ServerGlossSequenceMessage) => void;
    onSentence?: (message: ServerSentenceMessage) => void;
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

// One recognized sign of a finished utterance (docs/websocket-contract.md).
export interface GlossToken {
    gloss: string;
    confidence: number;
    startMs: number;
    endMs: number;
    status: GlossStatus;
    repeats: number;
}

// Sent when an utterance ends: the ordered signs with their confidence.
export interface ServerGlossSequenceMessage {
    type: "gloss_sequence";
    sessionId: string;
    utteranceId: number;
    glosses: GlossToken[];
    glossText: string;
    gaps: number[];
    startMs: number;
    endMs: number;
    boundary: string;
}

// Sent after the gloss sequence: the Armenian sentence from the NLP layer.
export interface ServerSentenceMessage {
    type: "sentence";
    sessionId: string;
    utteranceId: number;
    text: string;
    status: SentenceStatus;
    glossText: string;
    warnings: string[];
    provider: string | null;
    model: string | null;
    latencyMs: number;
}

export type ServerMessage =
    | ServerCaptionMessage
    | ServerStateMessage
    | ServerUnrecognizedMessage
    | ServerGlossSequenceMessage
    | ServerSentenceMessage
    | ServerErrorMessage;