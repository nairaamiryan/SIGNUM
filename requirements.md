# Functional Requirements Document (FRD)
## Sign Language Recognition System

---

## 1. General Overview
This document defines the functional requirements for the **Sign Language Recognition System**. The system is designed to operate via camera input: the user communicates using sign language, and the system translates and renders the speech into text (subtitles/captions) in real time.

> **Key Premise:** The system must recognize not only isolated static signs, but also complete sentences and continuous speech. This necessitates sequence modeling rather than isolated single-sign classification.

---

## 2. Supported Sign Types 
- **Static Signs (Single-frame handshapes):** Isolated letters or concepts that do not require movement.
- **Dynamic Signs (Motion-based signs):** Signs whose meaning depends on movement trajectory, speed, and direction.
- **Two-handed Signs:** Signs where both hands are involved and convey meaning through their relative positions and coordinated motion.
- **Sentence-level Sequences:** Continuous sequences of multiple signs interpreted as a coherent semantic unit (complete sentence).
- **Non-manual Markers:** Facial expressions, head orientation, and body posture that alter grammatical meaning (e.g., interrogative, negative).

---

## 3. Sign Recognition Rules 
- **Hand & Finger Pose Recognition:** The computer vision model analyzes hand skeletal landmarks frame by frame.
- **Motion Trajectory Analysis:** For dynamic signs, the hand’s direction, velocity, and trajectory shape are tracked and analyzed.
- **Temporal Segmentation:** The continuous video stream is segmented into individual sign boundaries.
- **Confidence Threshold:** A model prediction is considered valid only when its probability exceeds a defined threshold.
- **Sequence Modeling:** Individually recognized signs are aggregated and processed by a language model to construct grammatically correct sentences.
- **Contextual Correction:** The language model can correct ambiguous or noisy signs based on the broader context of the sentence.

---

## 4. Input and Output Requirements 

### Input
- **Real-time Video Stream:** Frame-by-frame capture from a live camera feed.
- **Skeletal Landmarks:** Frame-by-frame hand and body landmarks extracted via models such as MediaPipe, OpenPose, or similar tools.
- **Facial Landmarks:** Extracted facial landmarks for head pose and non-manual grammatical markers.
- **Frame Timestamps:** Temporal metadata per frame for precise motion and sequence analysis.

### Output
- **Text Transcription:** Real-time text display of the recognized sentence formatted as captions/subtitles.
- **Confidence Score:** Overall probability/confidence metric for the recognized sentence.
- **External Integrations:** Interface readiness for text-to-speech (TTS) synthesis or external text pipelines.
- **System State Indicator:** Real-time system status feedback (`Idle`, `Listening`, `Processing`, `Error`).

---

## 5. Handling Unrecognized and Ambiguous Signs 
- **Low-Confidence Signs:** If a prediction falls below the confidence threshold, the gesture is flagged as "unrecognized" and excluded from the sentence.
- **Ambiguous Signs:** When candidate signs have closely matched probabilities, the system uses sentence context to disambiguate and select the most probable sign.
- **Fallback Gesture:** A dedicated gesture or command allowing the user to repeat the last sign or restart the sentence from the beginning.
- **Visual Feedback Indicator:** Visual cues (e.g., warning badge, icon, color indicator) alerting the user that a gesture was unrecognized or ambiguous.
- **Timeout Rule:** If a sign or sentence remains incomplete after an extended idle period, the system flags the state and prompts the user to start a new sequence.

---

## 6. Continuous Gesture Input Processing 
- **Sliding Window Analysis:** Continuously evaluates the video stream across sequential temporal windows without waiting for the full utterance to complete.
- **Co-articulation & Transition Boundary Detection:** Distinguishes transitional hand movements between consecutive signs without requiring explicit pauses (inherent to natural sign language).
- **Buffer / Queue Management:** Temporarily buffers recent frames and candidate segments until sequence completion or continuation is established.
- **Occlusion & Frame Drop Tolerance:** Resilient against brief visual occlusions, motion blur, and dropped frames without invalidating the entire sequence.
- **Streaming Architecture:** Low-latency pipeline ensuring captions and subtitles are updated on screen in near real-time.

---

## 7. Gesture Lifecycle: Start, Progression, and End 
- **Start Detection:** The appearance and positioning of hands/body within the active camera frame marks the start of a signing sequence.
- **Progression Tracking:** Consecutive frames are continuously ingested and processed as part of the active sign/sentence until a termination event is detected.
- **End Detection:** Determined by stillness/motion cessation, hands returning to a neutral resting position, or an explicit user signal.
- **Thresholds and Timeouts:** Inactivity threshold (e.g., ~1.5–2.0 seconds of hand rest) automatically marks the sentence as finished.
- **Manual / Explicit Termination:** Option for the user to explicitly finalize or confirm a sentence (via a specific gesture, hotkey, or UI action).

---

## 8. Functional Edge Cases and Exceptions 
- **Camera & Frame Degradation:** Poor illumination, severe motion blur, partial hand occlusion, or user moving outside camera frame boundaries.
- **Multiple People or Extraneous Hands:** The system identifies and locks onto the primary signer while filtering out background persons or accidental hand appearances.
- **False Triggers:** Casual, non-signing gestures (e.g., scratching, adjusting glasses) must be filtered to prevent false activations.
- **Lighting & Video Quality Constraints:** Detection of low-light or degraded video conditions with prompt user notifications to adjust setup.
- **Visually Similar Signs:** Robust differentiation between closely matching sign patterns, backed by predefined disambiguation logic.
- **System Interruptions:** Graceful recovery and state cleanup during camera disconnects, packet loss, or application interruptions without producing corrupted text output.

---

## 9. Next Steps
1. Refine specifications for each section based on the chosen technology stack (model architecture, training/inference datasets).
2. Conduct review with Vahram Ghazaryan and the team.
3. Empirically determine concrete threshold and timeout values through iterative testing.
