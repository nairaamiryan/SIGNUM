import type { LandmarkFrame } from "./useHolisticLandmarks";

// Messages sent from the client to the Gesture Recognition Service.
export interface ClientLandmarksMessage {
    type: "landmarks";
    timestamp: number;
    leftHand: LandmarkFrame["leftHand"];
    rightHand: LandmarkFrame["rightHand"];
    face: LandmarkFrame["face"];
    pose: LandmarkFrame["pose"];
}

export interface ClientFinalizeMessage {
    type: "finalize";
}

export type ClientMessage = ClientLandmarksMessage | ClientFinalizeMessage;

// Messages received from the Gesture Recognition Service.
export interface ServerCaptionMessage {
    type: "caption";
    text: string;
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