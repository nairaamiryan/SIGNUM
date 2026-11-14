"""
Preprocessing utilities to convert landmark sequences (from Slovo dataset or live LandmarkFrames)
into SPOTER's standard 54-landmark (T, 54, 2) and (T, 108) tensor representations.
"""

from typing import Any, Sequence
import numpy as np
import torch


# 12 Upper-body landmarks mapped from MediaPipe Pose:
# nose=0, left_eye=2, right_eye=5, left_ear=7, right_ear=8,
# left_shoulder=11, right_shoulder=12, left_elbow=13, right_elbow=14,
# left_wrist=15, right_wrist=16
# Note: neck is computed as the midpoint of left_shoulder and right_shoulder.


def slovo_to_spoter_tensor(
    hand_0: Sequence[Sequence[Sequence[float]]],
    hand_1: Sequence[Sequence[Sequence[float]]],
    pose: Sequence[Sequence[Sequence[float]]],
    hand_0_mask: Sequence[bool] | None = None,
    hand_1_mask: Sequence[bool] | None = None,
) -> torch.Tensor:
    """
    Convert a single Slovo dataset sample into a (T, 54, 2) tensor.

    Args:
        hand_0: [T, 21, 3] Left hand coordinates (x, y, z)
        hand_1: [T, 21, 3] Right hand coordinates (x, y, z)
        pose: [T, 33, 3] MediaPipe Pose coordinates (x, y, z)
        hand_0_mask: Optional boolean sequence indicating if left hand is visible
        hand_1_mask: Optional boolean sequence indicating if right hand is visible

    Returns:
        torch.Tensor of shape (T, 54, 2) containing 2D (x, y) coordinates for:
        - [0:21]   Left hand (21 landmarks)
        - [21:42]  Right hand (21 landmarks)
        - [42:54]  Upper body pose (12 landmarks)
    """
    T = len(pose)
    out = np.zeros((T, 54, 2), dtype=np.float32)

    for t in range(T):
        # Left Hand (0..20)
        left_visible = (hand_0_mask is None) or bool(hand_0_mask[t])
        if left_visible and t < len(hand_0) and len(hand_0[t]) >= 21:
            for i in range(21):
                out[t, i, 0] = hand_0[t][i][0]
                out[t, i, 1] = hand_0[t][i][1]

        # Right Hand (21..41)
        right_visible = (hand_1_mask is None) or bool(hand_1_mask[t])
        if right_visible and t < len(hand_1) and len(hand_1[t]) >= 21:
            for i in range(21):
                out[t, 21 + i, 0] = hand_1[t][i][0]
                out[t, 21 + i, 1] = hand_1[t][i][1]

        # Upper-body Pose (42..53)
        if t < len(pose) and len(pose[t]) >= 17:
            p = pose[t]
            # 42: nose (MP 0)
            out[t, 42, 0] = p[0][0]
            out[t, 42, 1] = p[0][1]

            # 43: neck (midpoint of left_shoulder 11 and right_shoulder 12)
            out[t, 43, 0] = (p[11][0] + p[12][0]) / 2.0
            out[t, 43, 1] = (p[11][1] + p[12][1]) / 2.0

            # 44: right_eye (MP 5)
            out[t, 44, 0] = p[5][0]
            out[t, 44, 1] = p[5][1]

            # 45: left_eye (MP 2)
            out[t, 45, 0] = p[2][0]
            out[t, 45, 1] = p[2][1]

            # 46: right_ear (MP 8)
            out[t, 46, 0] = p[8][0]
            out[t, 46, 1] = p[8][1]

            # 47: left_ear (MP 7)
            out[t, 47, 0] = p[7][0]
            out[t, 47, 1] = p[7][1]

            # 48: right_shoulder (MP 12)
            out[t, 48, 0] = p[12][0]
            out[t, 48, 1] = p[12][1]

            # 49: left_shoulder (MP 11)
            out[t, 49, 0] = p[11][0]
            out[t, 49, 1] = p[11][1]

            # 50: right_elbow (MP 14)
            out[t, 50, 0] = p[14][0]
            out[t, 50, 1] = p[14][1]

            # 51: left_elbow (MP 13)
            out[t, 51, 0] = p[13][0]
            out[t, 51, 1] = p[13][1]

            # 52: right_wrist (MP 16)
            out[t, 52, 0] = p[16][0]
            out[t, 52, 1] = p[16][1]

            # 53: left_wrist (MP 15)
            out[t, 53, 0] = p[15][0]
            out[t, 53, 1] = p[15][1]

    return torch.from_numpy(out)


def frames_to_spoter_tensor(frames: Sequence[Any]) -> torch.Tensor:
    """
    Convert a sequence of LandmarkFrame objects from the gesture-service pipeline into a (T, 54, 2) tensor.

    Each frame is expected to have attributes or dictionary keys:
      - left_hand: 21 landmarks with 'x', 'y'
      - right_hand: 21 landmarks with 'x', 'y'
      - pose: 33 landmarks with 'x', 'y'
    """
    T = len(frames)
    out = np.zeros((T, 54, 2), dtype=np.float32)

    def _get_coord(obj: Any, key: str) -> float:
        if isinstance(obj, dict):
            return float(obj.get(key, 0.0))
        return float(getattr(obj, key, 0.0))

    def _get_list(frame: Any, attr: str):
        if isinstance(frame, dict):
            return frame.get(attr)
        return getattr(frame, attr, None)

    for t, frame in enumerate(frames):
        left_hand = _get_list(frame, "left_hand")
        right_hand = _get_list(frame, "right_hand")
        pose = _get_list(frame, "pose")

        # Left hand (0..20)
        if left_hand and len(left_hand) == 21:
            for i in range(21):
                out[t, i, 0] = _get_coord(left_hand[i], "x")
                out[t, i, 1] = _get_coord(left_hand[i], "y")

        # Right hand (21..41)
        if right_hand and len(right_hand) == 21:
            for i in range(21):
                out[t, 21 + i, 0] = _get_coord(right_hand[i], "x")
                out[t, 21 + i, 1] = _get_coord(right_hand[i], "y")

        # Upper-body pose (42..53)
        if pose and len(pose) >= 17:
            # 42: nose (MP 0)
            out[t, 42, 0] = _get_coord(pose[0], "x")
            out[t, 42, 1] = _get_coord(pose[0], "y")

            # 43: neck (midpoint of left_shoulder 11 and right_shoulder 12)
            out[t, 43, 0] = (_get_coord(pose[11], "x") + _get_coord(pose[12], "x")) / 2.0
            out[t, 43, 1] = (_get_coord(pose[11], "y") + _get_coord(pose[12], "y")) / 2.0

            # 44: right_eye (MP 5)
            out[t, 44, 0] = _get_coord(pose[5], "x")
            out[t, 44, 1] = _get_coord(pose[5], "y")

            # 45: left_eye (MP 2)
            out[t, 45, 0] = _get_coord(pose[2], "x")
            out[t, 45, 1] = _get_coord(pose[2], "y")

            # 46: right_ear (MP 8)
            out[t, 46, 0] = _get_coord(pose[8], "x")
            out[t, 46, 1] = _get_coord(pose[8], "y")

            # 47: left_ear (MP 7)
            out[t, 47, 0] = _get_coord(pose[7], "x")
            out[t, 47, 1] = _get_coord(pose[7], "y")

            # 48: right_shoulder (MP 12)
            out[t, 48, 0] = _get_coord(pose[12], "x")
            out[t, 48, 1] = _get_coord(pose[12], "y")

            # 49: left_shoulder (MP 11)
            out[t, 49, 0] = _get_coord(pose[11], "x")
            out[t, 49, 1] = _get_coord(pose[11], "y")

            # 50: right_elbow (MP 14)
            out[t, 50, 0] = _get_coord(pose[14], "x")
            out[t, 50, 1] = _get_coord(pose[14], "y")

            # 51: left_elbow (MP 13)
            out[t, 51, 0] = _get_coord(pose[13], "x")
            out[t, 51, 1] = _get_coord(pose[13], "y")

            # 52: right_wrist (MP 16)
            out[t, 52, 0] = _get_coord(pose[16], "x")
            out[t, 52, 1] = _get_coord(pose[16], "y")

            # 53: left_wrist (MP 15)
            out[t, 53, 0] = _get_coord(pose[15], "x")
            out[t, 53, 1] = _get_coord(pose[15], "y")

    return torch.from_numpy(out)
