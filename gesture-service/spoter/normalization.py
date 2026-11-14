"""
Body and hand landmark normalization based on the Boháček normalization algorithm
from the SPOTER paper: "Sign Pose-based Transformer for Word-level Sign Language Recognition".
"""

import math
import numpy as np
import torch


# Landmark slice indices in the 54-landmark tensor:
LEFT_HAND_SLICE = slice(0, 21)
RIGHT_HAND_SLICE = slice(21, 42)
BODY_SLICE = slice(42, 54)

# Indices relative to BODY_SLICE (0..11):
BODY_NOSE = 0
BODY_NECK = 1
BODY_RIGHT_EYE = 2
BODY_LEFT_EYE = 3
BODY_RIGHT_EAR = 4
BODY_LEFT_EAR = 5
BODY_RIGHT_SHOULDER = 6
BODY_LEFT_SHOULDER = 7
BODY_RIGHT_ELBOW = 8
BODY_LEFT_ELBOW = 9
BODY_RIGHT_WRIST = 10
BODY_LEFT_WRIST = 11


def normalize_spoter_tensor(tensor: torch.Tensor) -> torch.Tensor:
    """
    Apply SPOTER body and hand normalization to a (T, 54, 2) tensor.
    Following the original SPOTER pipeline:
    1. Normalizes upper-body pose within a head-metric bounding box.
    2. Normalizes hands within padded bounding boxes.
    3. Centers normalized coordinates by subtracting 0.5.

    Args:
        tensor: torch.Tensor of shape (T, 54, 2)
    Returns:
        Normalized torch.Tensor of shape (T, 54, 2)
    """
    device = tensor.device
    dtype = tensor.dtype
    data = tensor.clone().detach().cpu().numpy()
    T = data.shape[0]

    last_body_start = None
    last_body_end = None

    for t in range(T):
        # --- 1. BODY NORMALIZATION ---
        left_shoulder = data[t, 42 + BODY_LEFT_SHOULDER]
        right_shoulder = data[t, 42 + BODY_RIGHT_SHOULDER]
        neck = data[t, 42 + BODY_NECK]
        nose = data[t, 42 + BODY_NOSE]
        left_eye = data[t, 42 + BODY_LEFT_EYE]

        has_shoulders = (left_shoulder[0] != 0 or left_shoulder[1] != 0) and (
            right_shoulder[0] != 0 or right_shoulder[1] != 0
        )
        has_neck_nose = (neck[0] != 0 or neck[1] != 0) and (nose[0] != 0 or nose[1] != 0)

        if has_shoulders:
            dx = left_shoulder[0] - right_shoulder[0]
            dy = left_shoulder[1] - right_shoulder[1]
            head_metric = math.sqrt(dx * dx + dy * dy)
        elif has_neck_nose:
            dx = neck[0] - nose[0]
            dy = neck[1] - nose[1]
            head_metric = math.sqrt(dx * dx + dy * dy)
        elif last_body_start is not None:
            head_metric = None
        else:
            head_metric = 0.2  # default fallback

        if head_metric is not None and head_metric > 1e-4:
            neck_x = neck[0] if (neck[0] != 0 or neck[1] != 0) else (left_shoulder[0] + right_shoulder[0]) / 2.0
            eye_y = left_eye[1] if (left_eye[0] != 0 or left_eye[1] != 0) else (nose[1] + 0.05)

            start_x = neck_x - 3.0 * head_metric
            start_y = eye_y + head_metric
            end_x = neck_x + 3.0 * head_metric
            end_y = start_y - 6.0 * head_metric

            last_body_start = (start_x, start_y)
            last_body_end = (end_x, end_y)
        elif last_body_start is not None:
            start_x, start_y = last_body_start
            end_x, end_y = last_body_end
        else:
            start_x, start_y = 0.0, 1.0
            end_x, end_y = 1.0, 0.0

        box_w = end_x - start_x
        box_h = start_y - end_y  # inverted Y axis

        if abs(box_w) > 1e-6 and abs(box_h) > 1e-6:
            for i in range(42, 54):
                if data[t, i, 0] != 0 or data[t, i, 1] != 0:
                    data[t, i, 0] = (data[t, i, 0] - start_x) / box_w
                    data[t, i, 1] = (data[t, i, 1] - end_y) / box_h

        # --- 2. HAND NORMALIZATION ---
        for hand_slice in [LEFT_HAND_SLICE, RIGHT_HAND_SLICE]:
            hand_pts = data[t, hand_slice]
            valid_mask = (hand_pts[:, 0] != 0) | (hand_pts[:, 1] != 0)
            if not np.any(valid_mask):
                continue

            valid_x = hand_pts[valid_mask, 0]
            valid_y = hand_pts[valid_mask, 1]
            min_x, max_x = float(np.min(valid_x)), float(np.max(valid_x))
            min_y, max_y = float(np.min(valid_y)), float(np.max(valid_y))

            width = max_x - min_x
            height = max_y - min_y

            if width > height:
                delta_x = 0.1 * width
                delta_y = delta_x + ((width - height) / 2.0)
            else:
                delta_y = 0.1 * height
                delta_x = delta_y + ((height - width) / 2.0)

            h_start_x = min_x - delta_x
            h_end_x = max_x + delta_x
            h_start_y = min_y - delta_y
            h_end_y = max_y + delta_y

            hand_w = h_end_x - h_start_x
            hand_h = h_end_y - h_start_y

            if abs(hand_w) > 1e-6 and abs(hand_h) > 1e-6:
                for idx in range(hand_slice.start, hand_slice.stop):
                    if data[t, idx, 0] != 0 or data[t, idx, 1] != 0:
                        data[t, idx, 0] = (data[t, idx, 0] - h_start_x) / hand_w
                        data[t, idx, 1] = (data[t, idx, 1] - h_start_y) / hand_h

    # Subtract 0.5 to center coordinates around 0 (as in official SPOTER HF app)
    data = data - 0.5

    return torch.from_numpy(data).to(device=device, dtype=dtype)
