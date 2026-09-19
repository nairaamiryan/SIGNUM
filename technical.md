# Armenian Sign Language (ArSL) Real-Time Recognition and Captioning System

## 1. Introduction and System Architecture

The Armenian Sign Language (ArSL) Real-Time Recognition and Captioning System is designed to automatically recognize Armenian sign language gestures and convert them into readable Armenian text in real time. The system combines computer vision, machine learning, deep learning, and natural language processing technologies to provide accurate gesture recognition and sentence generation.

The primary objective of the system is to improve communication between hearing-impaired individuals and the wider community. Using a webcam, the system captures hand movements, identifies meaningful gestures, translates them into text, and displays the generated captions instantly on the screen.

---

## 2. System Architecture and Component Interaction

The system consists of several interconnected modules that work together to process video input and generate natural language output.

### Frontend Layer (Next.js + MediaPipe Hands)

The frontend application is developed using Next.js and React. It provides a user-friendly interface for accessing the webcam and displaying real-time subtitles.

MediaPipe Hands is responsible for detecting hand landmarks from each video frame. It extracts 21 hand key points, each represented by three-dimensional coordinates (x, y, z). Therefore, every frame produces 63 numerical features (21 × 3) that describe the position of the hand.

### Data Transmission Layer (WebSocket)

The extracted landmark coordinates are transmitted to the backend using WebSocket technology. This approach enables low-latency, bidirectional communication between the client and server, making real-time recognition possible.

### Gesture Spotting Service (FastAPI)

The first backend service is responsible for gesture spotting. This component analyzes continuous streams of hand landmark data and determines when a gesture starts and ends.

A sliding window algorithm is used to measure motion intensity across consecutive frames. If the movement exceeds a predefined threshold, the system marks the sequence as an active gesture segment and forwards it to the recognition service.

This stage helps eliminate unnecessary frames and reduces classification errors caused by random hand movements.

### Gesture Classification Service (FastAPI + PyTorch)

The classification service processes gesture segments received from the spotting module.

A Long Short-Term Memory (LSTM) neural network implemented in PyTorch is used to classify gesture sequences. The model receives temporal sequences of hand landmarks and predicts the corresponding gesture class (Gloss).

The input to the model consists of multiple frames, each containing 63 features. By analyzing both spatial and temporal information, the LSTM network can accurately recognize dynamic hand gestures.

Example gesture classes include:

| Class ID | Gloss     |
| -------- | --------- |
| 0        | Hello     |
| 1        | Water     |
| 2        | Thank You |
| 3        | I         |
| 4        | Want      |
| 5        | Home      |

Along with the predicted gesture, the model also outputs a confidence score indicating the reliability of the prediction.

### Natural Language Processing Layer (LLM Service)

Recognized gestures are converted into a sequence of glosses. However, sign language grammar often differs from spoken Armenian grammar.

To generate natural and grammatically correct Armenian sentences, the system uses a Large Language Model (LLM) such as Gemini API or Claude API.

For example:

**Input Gloss Sequence:**

I → Water → Want

**Generated Armenian Sentence:**

«Ես ջուր եմ ուզում։»

This module significantly improves readability and produces fluent Armenian text suitable for everyday communication.

### Database Layer (PostgreSQL)

PostgreSQL is used as the primary database system for storing recognition results and user session information.

The database maintains:

* User sessions
* Recognized gestures
* Confidence scores
* Landmark history
* Generated captions

Stored data can later be used for analytics, model improvement, and performance evaluation.

---

## 3. System Workflow

The complete workflow of the system can be summarized as follows:

1. The webcam captures live video.
2. MediaPipe Hands detects 21 hand landmarks.
3. Landmark coordinates are transmitted via WebSocket.
4. The Gesture Spotting Service identifies active gesture segments.
5. The Gesture Classification Service recognizes the gesture using an LSTM model.
6. The recognized gestures are converted into gloss sequences.
7. The LLM service transforms glosses into grammatically correct Armenian sentences.
8. The generated sentence is displayed on the screen as live subtitles.
9. Recognition results and captions are stored in PostgreSQL.

---

## 4. Database Design

The system database contains three primary entities:

### Sessions

Stores information about user interactions and active recognition sessions.

### Recognized Gestures

Stores detected gestures, confidence values, timestamps, and landmark data.

### Captions

Stores generated Armenian sentences and the corresponding gloss sequences.

The database structure ensures efficient storage, retrieval, and analysis of recognition results.

---

## 5. Technology Stack

| Layer                       | Technology                      | Purpose                                 |
| --------------------------- | ------------------------------- | --------------------------------------- |
| Frontend UI                 | Next.js 14, React, Tailwind CSS | Webcam interface and subtitle rendering |
| Pose Estimation             | MediaPipe Hands                 | Extraction of 21 hand landmarks         |
| Communication               | WebSockets                      | Real-time data transfer                 |
| Backend Services            | FastAPI                         | Asynchronous microservices              |
| Machine Learning            | PyTorch, LSTM                   | Gesture recognition and classification  |
| Natural Language Processing | Gemini API / Claude API         | Sentence generation                     |
| Database                    | PostgreSQL 16                   | Data storage and management             |
| Deployment                  | Docker, Docker Compose          | Containerized deployment                |

---

## 6. Conclusion

The Armenian Sign Language Real-Time Recognition and Captioning System provides a complete end-to-end solution for translating Armenian sign language into readable text. By combining MediaPipe Hands, FastAPI, PyTorch-based deep learning models, Large Language Models, and PostgreSQL, the system achieves real-time gesture recognition and natural language generation.

The proposed architecture is scalable, modular, and suitable for future improvements such as larger gesture vocabularies, sentence-level recognition, mobile deployment, and multimodal communication support.
