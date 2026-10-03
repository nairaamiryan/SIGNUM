// Messages sent from the client to the Gesture Recognition Service.
export interface ClientFrameMessage {
    type: "frame";
    timestamp: number;
    /** Base64-encoded JPEG frame. Will be replaced by landmark coordinates
     * once MediaPipe Holistic integration (separate subtask) is in place. */
    data: string;
}

export interface ClientFinalizeMessage {
    type: "finalize";
}

export type ClientMessage = ClientFrameMessage | ClientFinalizeMessage;

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