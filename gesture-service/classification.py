"""
Gesture classification using the SPOTER (Sign Pose-based Transformer) architecture.
Integrates trained SPOTER checkpoints for Armenian Sign Language recognition,
with automated body/hand pose normalization and graceful fallback to mock mode.
"""

from __future__ import annotations
import logging
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch
import torch.nn.functional as F

from constants import (
    DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD,
    DEFAULT_SPOTER_CHECKPOINT_PATH,
    DEFAULT_SPOTER_MODEL_NAME,
    DEFAULT_SPOTER_MODEL_VERSION,
    MOCK_CONFIDENCE,
)
from landmark_buffer import LandmarkFrame
from spoter.label_map import GlossLabelMap
from spoter.normalization import normalize_spoter_tensor
from spoter.preprocessing import frames_to_spoter_tensor
from spoter.spoter_model import SPOTER

logger = logging.getLogger("gesture-service.classification")

# Environment / configuration
MODEL_NAME = os.environ.get("SPOTER_MODEL_NAME", DEFAULT_SPOTER_MODEL_NAME)
MODEL_VERSION = os.environ.get("SPOTER_MODEL_VERSION", DEFAULT_SPOTER_MODEL_VERSION)
CHECKPOINT_PATH = os.environ.get("SPOTER_CHECKPOINT_PATH", DEFAULT_SPOTER_CHECKPOINT_PATH)
CONFIDENCE_THRESHOLD = float(
    os.environ.get("SPOTER_CONFIDENCE_THRESHOLD", str(DEFAULT_CLASSIFICATION_CONFIDENCE_THRESHOLD))
)

# Global model state
_model: Optional[SPOTER] = None
_label_map: Optional[GlossLabelMap] = None
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Mock fallback results when no checkpoint is present
_MOCK_RESULTS = [
    {"gloss": ["ԵՍ", "ՋՈՒՐ", "ՈՒԶԵԼ"], "text": "Ես ջուր եմ ուզում։"},
    {"gloss": ["ԲԱՐԵՎ"], "text": "Բարև։"},
    {"gloss": ["ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ"], "text": "Շնորհակալություն։"},
]


@dataclass
class ClassificationResult:
    gloss: list[str]
    text: str
    confidence: float
    model_name: str = MODEL_NAME
    model_version: str = MODEL_VERSION


def load_model(checkpoint_path: Optional[str] = None) -> bool:
    """
    Load SPOTER model checkpoint and associated label map into memory.
    Returns True if successfully loaded, False otherwise.
    """
    global _model, _label_map, MODEL_NAME, MODEL_VERSION, CHECKPOINT_PATH

    target_path = checkpoint_path or CHECKPOINT_PATH
    path = Path(target_path)

    if not path.is_file():
        logger.warning(
            "SPOTER checkpoint not found at '%s'. Running in fallback mock mode.",
            target_path,
            extra={"model_name": MODEL_NAME, "model_version": MODEL_VERSION},
        )
        _model = None
        _label_map = None
        return False

    try:
        checkpoint = torch.load(path, map_location=_device, weights_only=False)
        model = SPOTER.from_checkpoint(checkpoint, device=_device)
        num_classes = model.num_classes
        hidden_dim = model.hidden_dim


        label_map_data = checkpoint.get("label_map")
        if label_map_data:
            label_map = GlossLabelMap.from_dict(label_map_data)
        else:
            # Check for label_map.json next to checkpoint
            label_map_file = path.parent / "label_map.json"
            if label_map_file.exists():
                label_map = GlossLabelMap.load(label_map_file)
            else:
                raise ValueError("Checkpoint does not contain label map and label_map.json was not found.")

        _model = model
        _label_map = label_map
        MODEL_NAME = checkpoint.get("model_name", MODEL_NAME)
        MODEL_VERSION = checkpoint.get("model_version", MODEL_VERSION)

        logger.info(
            "Loaded SPOTER checkpoint: %s %s (%d classes, %d hidden_dim, device=%s) from %s",
            MODEL_NAME,
            MODEL_VERSION,
            num_classes,
            hidden_dim,
            _device,
            path,
            extra={"model_name": MODEL_NAME, "model_version": MODEL_VERSION, "audit": True},
        )
        return True

    except Exception:
        logger.exception("Failed to load SPOTER checkpoint from %s. Using fallback.", path)
        _model = None
        _label_map = None
        return False


def set_model(model: Optional[SPOTER], label_map: Optional[GlossLabelMap], name: str = "", version: str = ""):
    """Explicitly set or reset active model (useful for testing and hot-reloading)."""
    global _model, _label_map, MODEL_NAME, MODEL_VERSION
    _model = model
    _label_map = label_map
    if name:
        MODEL_NAME = name
    if version:
        MODEL_VERSION = version


def is_model_loaded() -> bool:
    """Return whether a real SPOTER model is loaded and ready for inference."""
    return _model is not None and _label_map is not None


def classify_segment(frames: list[LandmarkFrame]) -> Optional[ClassificationResult]:
    """
    Classify a buffered gesture segment into a predicted Armenian gloss and confidence score.
    Uses trained SPOTER model when loaded; falls back to mock results otherwise.
    """
    if not frames:
        return None

    # Fallback mode when model is not available
    if not is_model_loaded():
        res = random.choice(_MOCK_RESULTS)
        return ClassificationResult(
            gloss=res["gloss"],
            text=res["text"],
            confidence=MOCK_CONFIDENCE,
            model_name="mock",
            model_version="mock",
        )

    # 1. Convert frames to (T, 54, 2) tensor
    raw_tensor = frames_to_spoter_tensor(frames)

    # 2. Apply SPOTER body + hand normalization
    norm_tensor = normalize_spoter_tensor(raw_tensor)

    # 3. Reshape to (T, 108)
    t_len = norm_tensor.shape[0]
    inputs = norm_tensor.view(t_len, -1).to(_device)

    # 4. Model inference
    with torch.no_grad():
        outputs = _model(inputs).expand(1, -1, -1)  # (1, 1, num_classes)
        probs = F.softmax(outputs[0], dim=-1)[0]   # (num_classes,)

    top_prob, pred_idx_tensor = torch.max(probs, dim=-1)
    confidence = float(top_prob.item())
    pred_idx = int(pred_idx_tensor.item())

    # 5. Confidence check
    if confidence < CONFIDENCE_THRESHOLD:
        logger.debug(
            "Confidence %.3f below threshold %.3f (predicted class %d)",
            confidence,
            CONFIDENCE_THRESHOLD,
            pred_idx,
        )
        return None

    # 6. Map class index to Armenian gloss
    armenian_gloss = _label_map.decode(pred_idx)

    logger.info(
        "Classified gesture: gloss=%s, confidence=%.3f, model=%s, version=%s",
        armenian_gloss,
        confidence,
        MODEL_NAME,
        MODEL_VERSION,
        extra={"model_name": MODEL_NAME, "model_version": MODEL_VERSION, "confidence": confidence},
    )

    return ClassificationResult(
        gloss=[armenian_gloss],
        text=armenian_gloss,
        confidence=round(confidence, 4),
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
    )


# Automatically attempt to load model on module import
load_model()