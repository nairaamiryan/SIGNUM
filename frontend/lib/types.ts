import type { LandmarkFrame } from "./useHolisticLandmarks";

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
    state: "idle" | "listening" | "processing" | "error";
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