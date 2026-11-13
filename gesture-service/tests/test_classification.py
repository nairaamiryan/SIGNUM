"""
Unit and integration tests for the SPOTER gesture classification component.
"""

import os
from pathlib import Path
import tempfile
import pytest
import torch
import torch.nn as nn

from landmark_buffer import LandmarkFrame
from spoter.gaussian_noise import GaussianNoise
from spoter.label_map import GlossLabelMap, russian_gloss_to_armenian
from spoter.normalization import normalize_spoter_tensor
from spoter.preprocessing import frames_to_spoter_tensor, slovo_to_spoter_tensor
from spoter.spoter_model import SPOTER
import classification
from classification import (
    ClassificationResult,
    classify_segment,
    is_model_loaded,
    set_model,
)


def _make_dummy_frame(t: int = 0) -> LandmarkFrame:
    # 21 left hand points
    lh = [{"x": 0.2 + 0.01 * i, "y": 0.5 + 0.01 * i, "z": 0.0} for i in range(21)]
    # 21 right hand points
    rh = [{"x": 0.7 + 0.01 * i, "y": 0.5 + 0.01 * i, "z": 0.0} for i in range(21)]
    # 33 pose points (upper body indices 0..16 populated)
    pose = [{"x": 0.5 + 0.01 * i, "y": 0.2 + 0.02 * i, "z": 0.0} for i in range(33)]
    # Ensure shoulders are well-defined
    pose[11] = {"x": 0.4, "y": 0.3, "z": 0.0}  # left shoulder
    pose[12] = {"x": 0.6, "y": 0.3, "z": 0.0}  # right shoulder
    pose[0] = {"x": 0.5, "y": 0.15, "z": 0.0}  # nose
    pose[2] = {"x": 0.45, "y": 0.14, "z": 0.0} # left eye
    pose[5] = {"x": 0.55, "y": 0.14, "z": 0.0} # right eye

    return LandmarkFrame(
        timestamp=1000 + t * 50,
        left_hand=lh,
        right_hand=rh,
        pose=pose,
    )


def test_frames_to_spoter_tensor():
    frames = [_make_dummy_frame(i) for i in range(10)]
    tensor = frames_to_spoter_tensor(frames)

    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (10, 54, 2)
    assert tensor.dtype == torch.float32

    # Verify left hand at [0, 0] matches dummy frame
    assert pytest.approx(tensor[0, 0, 0].item(), rel=1e-3) == 0.2
    assert pytest.approx(tensor[0, 0, 1].item(), rel=1e-3) == 0.5

    # Verify right hand at [0, 21] matches
    assert pytest.approx(tensor[0, 21, 0].item(), rel=1e-3) == 0.7

    # Verify neck (midpoint of left shoulder 0.4 and right shoulder 0.6 = 0.5)
    assert pytest.approx(tensor[0, 43, 0].item(), rel=1e-3) == 0.5
    assert pytest.approx(tensor[0, 43, 1].item(), rel=1e-3) == 0.3


def test_slovo_to_spoter_tensor():
    T = 5
    hand_0 = [[[0.1, 0.2, 0.0]] * 21] * T
    hand_1 = [[[0.8, 0.7, 0.0]] * 21] * T
    pose = [[[0.5, 0.4, 0.0]] * 33] * T

    tensor = slovo_to_spoter_tensor(hand_0, hand_1, pose)
    assert tensor.shape == (T, 54, 2)
    assert pytest.approx(tensor[0, 0, 0].item(), rel=1e-3) == 0.1
    assert pytest.approx(tensor[0, 21, 0].item(), rel=1e-3) == 0.8


def test_normalize_spoter_tensor():
    frames = [_make_dummy_frame(i) for i in range(8)]
    raw = frames_to_spoter_tensor(frames)
    norm = normalize_spoter_tensor(raw)

    assert norm.shape == (8, 54, 2)
    assert not torch.isnan(norm).any()
    assert not torch.isinf(norm).any()


def test_gaussian_noise():
    tensor = torch.zeros((10, 108))
    noise = GaussianNoise(mean=0.0, std=0.05)
    augmented = noise(tensor)

    assert augmented.shape == (10, 108)
    assert not torch.allclose(tensor, augmented)
    # Mean of noise should be close to 0
    assert abs(augmented.mean().item()) < 0.05


def test_russian_to_armenian_gloss_mapping():
    assert russian_gloss_to_armenian("привет") == "ԲԱՐԵՎ"
    assert russian_gloss_to_armenian("спасибо") == "ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ"
    assert russian_gloss_to_armenian("вода") == "ՋՈՒՐ"
    assert russian_gloss_to_armenian("мама") == "ՄԱՅՐԻԿ"

    # Non-core words map phonetically rather than erroring
    non_core = russian_gloss_to_armenian("стол")
    assert isinstance(non_core, str)
    assert len(non_core) > 0


def test_gloss_label_map_serialization():
    glosses = ["привет", "спасибо", "вода"]
    lmap = GlossLabelMap.from_russian_glosses(glosses)
    assert lmap.num_classes == 3

    encoded = lmap.encode("ԲԱՐԵՎ")
    assert lmap.decode(encoded) == "ԲԱՐԵՎ"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir) / "label_map.json"
        lmap.save(tmp_path)
        loaded = GlossLabelMap.load(tmp_path)

        assert loaded.num_classes == 3
        assert loaded.decode(encoded) == "ԲԱՐԵՎ"


def test_spoter_architecture():
    num_classes = 4
    model = SPOTER(num_classes=num_classes, hidden_dim=108, nhead=9, num_encoder_layers=2, num_decoder_layers=2)

    # 1. 2D single sequence input: (T=15, hidden_dim=108)
    x_single = torch.randn(15, 108)
    out_single = model(x_single)
    assert out_single.shape == (1, 1, num_classes)

    # 2. 3D batched input: (B=2, T=15, hidden_dim=108)
    x_batched = torch.randn(2, 15, 108)
    out_batched = model(x_batched)
    assert out_batched.shape == (2, 1, num_classes)


def test_classify_segment_fallback_when_no_model():
    # Ensure model is None
    set_model(None, None)
    assert not is_model_loaded()

    frames = [_make_dummy_frame(i) for i in range(5)]
    res = classify_segment(frames)

    assert res is not None
    assert isinstance(res, ClassificationResult)
    assert len(res.gloss) > 0
    assert res.confidence == 0.75
    assert res.model_name == "mock"


def test_classify_segment_with_loaded_model():
    num_classes = 3
    model = SPOTER(num_classes=num_classes, hidden_dim=108, nhead=9, num_encoder_layers=2, num_decoder_layers=2)
    model.eval()

    label_map = GlossLabelMap(idx_to_gloss={0: "ԲԱՐԵՎ", 1: "ՋՈՒՐ", 2: "ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ"})
    set_model(model, label_map, name="spoter_test", version="v1")

    assert is_model_loaded()

    frames = [_make_dummy_frame(i) for i in range(12)]
    res = classify_segment(frames)

    # Either returns a prediction above threshold or None if below
    if res is not None:
        assert res.gloss[0] in ["ԲԱՐԵՎ", "ՋՈՒՐ", "ՇՆՈՐՀԱԿԱԼՈՒԹՅՈՒՆ"]
        assert 0.0 <= res.confidence <= 1.0
        assert res.model_name == "spoter_test"
        assert res.model_version == "v1"

    # Reset back to uninitialized state
    set_model(None, None)
