"""
Prepare and convert the Slovo MediaPipe Landmarks dataset into SPOTER-ready tensors.
Performs:
1. Extraction of 54 landmarks (21 left hand + 21 right hand + 12 upper-body pose).
2. SPOTER body + hand normalization.
3. Russian gloss -> Armenian gloss mapping and index encoding.
4. Saves serialized PyTorch .pt datasets and label_map.json.

Can fetch from HuggingFace Datasets Server API (no pandas/pyarrow C-extension required)
or from local directory if cached.
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple
import torch

# Ensure parent directory is in sys.path to import spoter package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spoter.label_map import GlossLabelMap, russian_gloss_to_armenian
from spoter.normalization import normalize_spoter_tensor
from spoter.preprocessing import slovo_to_spoter_tensor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepare_dataset")


def fetch_hf_rows(split: str, offset: int, length: int = 50) -> List[dict]:
    """Fetch a slice of rows from the HuggingFace Datasets Server API."""
    url = (
        f"https://datasets-server.huggingface.co/rows"
        f"?dataset=karinversan/slovo-full-landmarks&config=default&split={split}&offset={offset}&length={length}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "SIGNUM-SPOTER/1.0 (Mozilla/5.0)"}
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [r["row"] for r in data.get("rows", [])]
        except Exception as exc:
            logger.warning("Attempt %d failed to fetch %s (offset %d): %s. Retrying...", attempt + 1, split, offset, exc)
            time.sleep(2 ** attempt)
    return []


def process_sample(sample: dict, label_map: GlossLabelMap) -> Tuple[torch.Tensor, int] | None:
    """Process a single raw sample into (flattened_tensor, label_idx)."""
    gloss = (sample.get("gloss") or sample.get("text") or "").strip()
    if not gloss:
        return None

    arm_gloss = russian_gloss_to_armenian(gloss)
    try:
        label_idx = label_map.encode(arm_gloss)
    except KeyError:
        return None

    hand_0 = sample.get("hand_0")
    hand_1 = sample.get("hand_1")
    pose = sample.get("pose")
    hand_0_mask = sample.get("hand_0_mask")
    hand_1_mask = sample.get("hand_1_mask")

    if not pose or len(pose) == 0:
        return None

    # 1. Extract 54 landmarks: (T, 54, 2)
    raw_tensor = slovo_to_spoter_tensor(
        hand_0=hand_0 or [],
        hand_1=hand_1 or [],
        pose=pose,
        hand_0_mask=hand_0_mask,
        hand_1_mask=hand_1_mask,
    )

    # 2. Apply SPOTER body + hand normalization
    norm_tensor = normalize_spoter_tensor(raw_tensor)

    # 3. Flatten to (T, 108)
    t_len = norm_tensor.shape[0]
    flattened = norm_tensor.view(t_len, -1)

    return flattened, label_idx


def prepare(
    output_dir: str = "data",
    max_train_samples: int = 300,
    max_test_samples: int = 60,
    batch_fetch_size: int = 50,
):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Fetching %d training samples from Hugging Face API...", max_train_samples)
    train_raw: List[dict] = []
    offset = 0
    while len(train_raw) < max_train_samples:
        chunk = fetch_hf_rows("train", offset=offset, length=min(batch_fetch_size, max_train_samples - len(train_raw)))
        if not chunk:
            break
        train_raw.extend(chunk)
        offset += len(chunk)
        logger.info("Fetched %d / %d train samples", len(train_raw), max_train_samples)

    logger.info("Fetching %d test samples from Hugging Face API...", max_test_samples)
    test_raw: List[dict] = []
    offset = 0
    while len(test_raw) < max_test_samples:
        chunk = fetch_hf_rows("test", offset=offset, length=min(batch_fetch_size, max_test_samples - len(test_raw)))
        if not chunk:
            break
        test_raw.extend(chunk)
        offset += len(chunk)
        logger.info("Fetched %d / %d test samples", len(test_raw), max_test_samples)

    # Collect unique glosses across downloaded train and test samples
    glosses_set = set()
    for s in train_raw + test_raw:
        g = (s.get("gloss") or s.get("text") or "").strip()
        if g:
            glosses_set.add(g)

    sorted_glosses = sorted(list(glosses_set))
    logger.info("Building label map for %d unique gloss classes...", len(sorted_glosses))
    label_map = GlossLabelMap.from_russian_glosses(sorted_glosses)
    label_map_path = out_dir / "label_map.json"
    label_map.save(label_map_path)

    # Process train split
    train_data: List[Tuple[torch.Tensor, int]] = []
    for s in train_raw:
        res = process_sample(s, label_map)
        if res is not None:
            train_data.append(res)

    train_pt_path = out_dir / "train.pt"
    torch.save(train_data, train_pt_path)
    logger.info("Saved %d processed training samples to %s", len(train_data), train_pt_path)

    # Process test split
    test_data: List[Tuple[torch.Tensor, int]] = []
    for s in test_raw:
        res = process_sample(s, label_map)
        if res is not None:
            test_data.append(res)

    test_pt_path = out_dir / "test.pt"
    torch.save(test_data, test_pt_path)
    logger.info("Saved %d processed test samples to %s", len(test_data), test_pt_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Slovo dataset for SPOTER training")
    parser.add_argument("--output_dir", type=str, default="data", help="Directory to save .pt and label_map.json")
    parser.add_argument("--max_train_samples", type=int, default=300, help="Train samples to fetch and prepare")
    parser.add_argument("--max_test_samples", type=int, default=60, help="Test samples to fetch and prepare")
    parser.add_argument("--batch_fetch_size", type=int, default=50, help="Batch size for API fetches")
    args = parser.parse_args()

    prepare(
        output_dir=args.output_dir,
        max_train_samples=args.max_train_samples,
        max_test_samples=args.max_test_samples,
        batch_fetch_size=args.batch_fetch_size,
    )
