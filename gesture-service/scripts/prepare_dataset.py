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
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import torch

# Ensure parent directory is in sys.path to import spoter package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spoter.label_map import GlossLabelMap, RUSSIAN_TO_ARMENIAN_CORE, russian_gloss_to_armenian
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
    dataset_dir: Optional[str] = None,
    max_train_samples: Optional[int] = None,
    max_test_samples: Optional[int] = None,
    batch_fetch_size: int = 50,
    top_k_classes: Optional[int] = None,
    core_only: bool = False,
):
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if dataset_dir and Path(dataset_dir).exists():
        from datasets import load_from_disk

        logger.info("Loading local dataset from %s...", dataset_dir)
        ds = load_from_disk(dataset_dir)
        needed_cols = ["gloss", "text", "hand_0", "hand_1", "pose", "hand_0_mask", "hand_1_mask"]
        train_split = ds["train"]
        avail_cols = [c for c in needed_cols if c in train_split.column_names]
        train_split = train_split.select_columns(avail_cols)
        test_split = ds.get("test") or ds.get("validation")
        if test_split is not None:
            test_split = test_split.select_columns([c for c in needed_cols if c in test_split.column_names])
        if max_train_samples:
            train_split = train_split.select(range(min(max_train_samples, len(train_split))))
        if test_split is not None and max_test_samples:
            test_split = test_split.select(range(min(max_test_samples, len(test_split))))
        train_raw = train_split
        test_raw = test_split if test_split is not None else []
        logger.info("Loaded %d train and %d test samples from disk.", len(train_raw), len(test_raw))
    else:
        max_tr = max_train_samples or 300
        max_te = max_test_samples or 60
        logger.info("Fetching %d training samples from Hugging Face API...", max_tr)
        train_raw: List[dict] = []
        offset = 0
        while len(train_raw) < max_tr:
            chunk = fetch_hf_rows("train", offset=offset, length=min(batch_fetch_size, max_tr - len(train_raw)))
            if not chunk:
                break
            train_raw.extend(chunk)
            offset += len(chunk)
            logger.info("Fetched %d / %d train samples", len(train_raw), max_tr)

        logger.info("Fetching %d test samples from Hugging Face API...", max_te)
        test_raw: List[dict] = []
        offset = 0
        while len(test_raw) < max_te:
            chunk = fetch_hf_rows("test", offset=offset, length=min(batch_fetch_size, max_te - len(test_raw)))
            if not chunk:
                break
            test_raw.extend(chunk)
            offset += len(chunk)
            logger.info("Fetched %d / %d test samples", len(test_raw), max_te)

    # Collect gloss counts across train samples (excluding 'no_event')
    gloss_counts: Counter[str] = Counter()
    if hasattr(train_raw, "column_names"):
        col = "gloss" if "gloss" in train_raw.column_names else "text"
        for g in train_raw[col]:
            g_str = (g or "").strip()
            if g_str and g_str != "no_event":
                gloss_counts[g_str] += 1
    else:
        for s in train_raw:
            g = (s.get("gloss") or s.get("text") or "").strip()
            if g and g != "no_event":
                gloss_counts[g] += 1

    if core_only:
        gloss_counts = Counter({g: c for g, c in gloss_counts.items() if g.lower() in RUSSIAN_TO_ARMENIAN_CORE})
        logger.info("Filtered to %d curated core Armenian classes.", len(gloss_counts))

    if top_k_classes:
        selected_glosses = [g for g, _ in gloss_counts.most_common(top_k_classes)]
        logger.info("Selected top %d most frequent classes.", len(selected_glosses))
    else:
        selected_glosses = list(gloss_counts.keys())

    sorted_glosses = sorted(selected_glosses)
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
    parser.add_argument("--dataset_dir", type=str, default=None, help="Local dataset directory saved by download_dataset.py")
    parser.add_argument("--max_train_samples", type=int, default=None, help="Train samples to prepare")
    parser.add_argument("--max_test_samples", type=int, default=None, help="Test samples to prepare")
    parser.add_argument("--batch_fetch_size", type=int, default=50, help="Batch size for API fetches")
    parser.add_argument("--top_k_classes", type=int, default=None, help="Optional limit to top K most frequent classes")
    parser.add_argument("--core_only", action="store_true", help="Filter to curated RUSSIAN_TO_ARMENIAN_CORE classes")
    args = parser.parse_args()

    prepare(
        output_dir=args.output_dir,
        dataset_dir=args.dataset_dir,
        max_train_samples=args.max_train_samples,
        max_test_samples=args.max_test_samples,
        batch_fetch_size=args.batch_fetch_size,
        top_k_classes=args.top_k_classes,
        core_only=args.core_only,
    )
