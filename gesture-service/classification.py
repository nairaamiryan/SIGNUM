"""
Gesture classification.

# TODO: Mock implementation — replace with the actual SPOTER
# (Sign Pose-based Transformer) model integration once a trained
# checkpoint for the Armenian Sign Language dataset is available.
#
# The real implementation should:
#   1. Normalize/reshape the buffered landmark frames into the exact
#      input tensor shape expected by the trained SPOTER model
#      (dimensionality to be finalized per KAN-13).
#   2. Run inference to obtain a gloss sequence and confidence score.
#   3. Pass the gloss sequence to the NLP/LLM service for sentence
#      generation (separate service, not handled here).
#
# Until the real model is wired in, this module returns a random mock
# result so the full pipeline (spotting -> classification -> WebSocket
# response) can be exercised end-to-end.
"""

import random
from dataclasses import dataclass

from constants import MOCK_CONFIDENCE
from landmark_buffer import LandmarkFrame

# TODO: Mock implementation — replace with real gloss vocabulary / model output.
_MOCK_RESULTS = [
    {"gloss": ["ԵՍ", "ՋՈՒՐ", "ՈՒԶԵԼ"], "text": "Ես ջուր եմ ուզում։"},
    {"gloss": ["ԲԱՐԵՒ"], "text": "Բարև։"},
    {"gloss": ["ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ"], "text": "Շնորհակալություն։"},
]


@dataclass
class ClassificationResult:
    gloss: list[str]
    text: str
    confidence: float


def classify_segment(frames: list[LandmarkFrame]) -> ClassificationResult | None:
    """Classifies a buffered gesture segment into a gloss sequence and
    generated sentence.

    # TODO: Mock implementation — replace with the actual SPOTER model
    # inference call. Currently ignores `frames` entirely and returns a
    # random canned result.
    """
    if not frames:
        return None

    result = random.choice(_MOCK_RESULTS)
    return ClassificationResult(
        gloss=result["gloss"],
        text=result["text"],
        confidence=MOCK_CONFIDENCE,
    )