"""
Evaluate a trained SPOTER checkpoint on the test set.
Computes top-1 and top-5 accuracy, per-class metrics, and generates an evaluation report.
"""

from __future__ import annotations
import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List, Tuple
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from spoter.label_map import GlossLabelMap
from spoter.spoter_model import SPOTER

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_spoter")


def evaluate_checkpoint(
    checkpoint_path: str = "models/spoter_arsl_v1.pth",
    test_data_path: str = "data/test.pt",
    force_cpu: bool = False,
    top_k: int = 5,
):
    ckpt_path = Path(checkpoint_path)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found at {ckpt_path}")

    device = torch.device("cuda" if torch.cuda.is_available() and not force_cpu else "cpu")
    logger.info("Using device: %s", device)

    logger.info("Loading checkpoint from %s ...", ckpt_path)
    checkpoint = torch.load(ckpt_path, map_location=device, weights_only=False)

    model = SPOTER.from_checkpoint(checkpoint, device=device)
    num_classes = model.num_classes
    label_map_data = checkpoint["label_map"]
    label_map = GlossLabelMap.from_dict(label_map_data)


    logger.info("Model loaded (%d classes, %d hidden_dim).", num_classes, model.hidden_dim)

    test_path = Path(test_data_path)
    if not test_path.exists():
        raise FileNotFoundError(f"Test data not found at {test_path}")

    logger.info("Loading test data from %s ...", test_path)
    test_data: List[Tuple[torch.Tensor, int]] = torch.load(test_path, weights_only=False)
    logger.info("Loaded %d test samples.", len(test_data))

    total = len(test_data)
    top1_correct = 0
    topk_correct = 0

    class_stats: Dict[int, Dict[str, int]] = {i: {"total": 0, "correct": 0} for i in range(num_classes)}

    with torch.no_grad():
        for i, (tensor, label_idx) in enumerate(test_data):
            inputs = tensor.to(device)
            # Forward pass: shape (T, 108) -> (1, 1, num_classes)
            outputs = model(inputs).expand(1, -1, -1)
            logits = outputs[0]  # (1, num_classes)
            probs = F.softmax(logits, dim=-1)[0]  # (num_classes,)

            pred_top1 = int(torch.argmax(probs).item())
            k_val = min(top_k, num_classes)
            topk_preds = torch.topk(probs, k_val).indices.tolist()

            class_stats[label_idx]["total"] += 1
            if pred_top1 == label_idx:
                top1_correct += 1
                class_stats[label_idx]["correct"] += 1

            if label_idx in topk_preds:
                topk_correct += 1

    top1_acc = (top1_correct / total) * 100.0 if total > 0 else 0.0
    topk_acc = (topk_correct / total) * 100.0 if total > 0 else 0.0

    print("\n" + "=" * 60)
    print("SPOTER EVALUATION REPORT")
    print("=" * 60)
    print(f"Checkpoint:       {ckpt_path.name}")
    print(f"Model Name/Ver:   {checkpoint.get('model_name', 'spoter_arsl')} ({checkpoint.get('model_version', 'v1')})")
    print(f"Total Test Set:   {total} samples")
    print(f"Total Classes:    {num_classes}")
    print(f"Top-1 Accuracy:   {top1_acc:.2f}% ({top1_correct}/{total})")
    print(f"Top-{top_k} Accuracy:   {topk_acc:.2f}% ({topk_correct}/{total})")
    print("-" * 60)

    # Class performance breakdown
    active_classes = [c for c in class_stats if class_stats[c]["total"] > 0]
    active_classes.sort(
        key=lambda c: class_stats[c]["correct"] / class_stats[c]["total"], reverse=True
    )

    print("Top Recognized Classes:")
    for c in active_classes[:10]:
        acc = (class_stats[c]["correct"] / class_stats[c]["total"]) * 100.0
        gloss = label_map.decode(c)
        print(f"  {gloss:15s} (Class {c:3d}): {acc:5.1f}% ({class_stats[c]['correct']}/{class_stats[c]['total']})")

    print("\nLowest Accuracy Classes:")
    for c in active_classes[-10:]:
        acc = (class_stats[c]["correct"] / class_stats[c]["total"]) * 100.0
        gloss = label_map.decode(c)
        print(f"  {gloss:15s} (Class {c:3d}): {acc:5.1f}% ({class_stats[c]['correct']}/{class_stats[c]['total']})")
    print("=" * 60 + "\n")

    report = {
        "checkpoint": str(ckpt_path),
        "total_samples": total,
        "num_classes": num_classes,
        "top1_accuracy": top1_acc,
        f"top{top_k}_accuracy": topk_acc,
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate SPOTER checkpoint")
    parser.add_argument("--checkpoint", type=str, default="models/spoter_arsl_v1.pth", help="Checkpoint path")
    parser.add_argument("--test_data", type=str, default="data/test.pt", help="Path to test.pt")
    parser.add_argument("--top_k", type=int, default=5, help="Top-K accuracy")
    parser.add_argument("--force_cpu", action="store_true", help="Force CPU")
    args = parser.parse_args()

    evaluate_checkpoint(
        checkpoint_path=args.checkpoint,
        test_data_path=args.test_data,
        force_cpu=args.force_cpu,
        top_k=args.top_k,
    )
