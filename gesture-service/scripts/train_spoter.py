"""
Train the SPOTER (Sign Pose-based Transformer) model on sign language landmark data.
Reference: Boháček & Hrúz, WACV 2022.
"""

from __future__ import annotations
import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path
from typing import List, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spoter.gaussian_noise import GaussianNoise
from spoter.label_map import GlossLabelMap
from spoter.spoter_model import SPOTER

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_spoter")


class LandmarkDataset(Dataset):
    def __init__(self, data: List[Tuple[torch.Tensor, int]], transform=None):
        self.data = data
        self.transform = transform

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        tensor, label = self.data[idx]
        if self.transform is not None:
            tensor = self.transform(tensor)
        return tensor, label


def collate_single(batch):
    # For batch_size=1: returns (tensor, label, None)
    tensor, label = batch[0]
    return tensor, torch.tensor([label], dtype=torch.long), None


def collate_padded(batch):
    # For batch_size > 1: pad sequences to max length in batch and build padding mask
    tensors, labels = zip(*batch)
    max_len = max(t.shape[0] for t in tensors)
    hidden_dim = tensors[0].shape[1]
    batch_size = len(tensors)

    padded = torch.zeros((batch_size, max_len, hidden_dim), dtype=torch.float32)
    pad_mask = torch.ones((batch_size, max_len), dtype=torch.bool)
    for i, t in enumerate(tensors):
        seq_len = t.shape[0]
        padded[i, :seq_len, :] = t
        pad_mask[i, :seq_len] = False

    return padded, torch.tensor(labels, dtype=torch.long), pad_mask


def evaluate(model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device):
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, labels, pad_mask in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            if pad_mask is not None:
                pad_mask = pad_mask.to(device)

            if inputs.dim() == 2:
                # Shape (T, 108)
                outputs = model(inputs).expand(1, -1, -1)  # (1, 1, num_classes)
                loss = criterion(outputs[0], labels)
                pred = torch.argmax(outputs[0], dim=-1)
                correct += int((pred == labels).sum().item())
                total += 1
            else:
                # Batched: (B, T, 108)
                outputs = model(inputs, src_key_padding_mask=pad_mask)  # (B, 1, num_classes)
                logits = outputs.squeeze(1)  # (B, num_classes)
                loss = criterion(logits, labels)
                pred = torch.argmax(logits, dim=-1)
                correct += int((pred == labels).sum().item())
                total += labels.size(0)

            total_loss += loss.item()

    avg_loss = total_loss / max(1, len(loader))
    acc = correct / max(1, total)
    return avg_loss, acc


def train(args):
    # Set random seeds
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # Determine device
    if torch.cuda.is_available() and not args.force_cpu:
        device = torch.device("cuda")
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 2)
        logger.info("Using CUDA GPU: %s (%.0f MB VRAM)", gpu_name, gpu_mem)
    elif torch.backends.mps.is_available() and not args.force_cpu:
        device = torch.device("mps")
        logger.info("Using Apple Silicon MPS GPU.")
    else:
        device = torch.device("cpu")
        logger.info("Using CPU device.")

    # Load Label Map
    label_map_path = Path(args.label_map)
    if not label_map_path.exists():
        raise FileNotFoundError(f"Label map not found at {label_map_path}")
    label_map = GlossLabelMap.load(label_map_path)
    num_classes = label_map.num_classes
    logger.info("Loaded label map with %d classes.", num_classes)

    # Load Data
    train_path = Path(args.train_data)
    test_path = Path(args.test_data)

    if not train_path.exists():
        raise FileNotFoundError(f"Train data not found at {train_path}")

    logger.info("Loading training data from %s...", train_path)
    train_samples = torch.load(train_path, weights_only=False)
    logger.info("Loaded %d training samples.", len(train_samples))

    if test_path.exists():
        logger.info("Loading test data from %s...", test_path)
        test_samples = torch.load(test_path, weights_only=False)
        logger.info("Loaded %d test samples.", len(test_samples))
    else:
        # Split 20% from train if test_data not provided
        val_size = max(1, int(0.2 * len(train_samples)))
        test_samples = train_samples[-val_size:]
        train_samples = train_samples[:-val_size]
        logger.info("Split validation set: %d train, %d val", len(train_samples), len(test_samples))

    # Datasets and Loaders
    aug = GaussianNoise(mean=0.0, std=args.gaussian_std) if args.gaussian_std > 0 else None
    train_ds = LandmarkDataset(train_samples, transform=aug)
    val_ds = LandmarkDataset(test_samples, transform=None)

    collate_fn = collate_single if args.batch_size == 1 else collate_padded
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=collate_fn)

    # Model
    model = SPOTER(
        num_classes=num_classes,
        hidden_dim=args.hidden_dim,
        nhead=args.nhead,
        num_encoder_layers=args.num_encoder_layers,
        num_decoder_layers=args.num_decoder_layers,
    )
    model.to(device)

    # Optimizer, Criterion, Scheduler
    criterion = nn.CrossEntropyLoss()
    if args.optimizer.lower() == "adamw":
        optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    else:
        optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=0.9, nesterov=True)

    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=args.scheduler_factor, patience=args.scheduler_patience
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = out_dir / f"{args.model_name}_{args.model_version}.pth"

    best_val_acc = 0.0
    logger.info("Starting training for %d epochs...", args.epochs)

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        train_correct = 0
        train_total = 0

        for inputs, labels, pad_mask in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            if pad_mask is not None:
                pad_mask = pad_mask.to(device)

            optimizer.zero_grad()

            if inputs.dim() == 2:
                outputs = model(inputs).expand(1, -1, -1)  # (1, 1, num_classes)
                loss = criterion(outputs[0], labels)
                pred = torch.argmax(outputs[0], dim=-1)
                train_correct += int((pred == labels).sum().item())
                train_total += 1
            else:
                outputs = model(inputs, src_key_padding_mask=pad_mask)  # (B, 1, num_classes)
                logits = outputs.squeeze(1)
                loss = criterion(logits, labels)
                pred = torch.argmax(logits, dim=-1)
                train_correct += int((pred == labels).sum().item())
                train_total += labels.size(0)

            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        train_loss = running_loss / max(1, len(train_loader))
        train_acc = train_correct / max(1, train_total)

        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        scheduler.step(val_acc)
        current_lr = optimizer.param_groups[0]["lr"]

        logger.info(
            "Epoch [%d/%d] | Train Loss: %.4f, Acc: %.2f%% | Val Loss: %.4f, Acc: %.2f%% | LR: %.6f",
            epoch, args.epochs, train_loss, train_acc * 100.0, val_loss, val_acc * 100.0, current_lr
        )

        if val_acc >= best_val_acc or epoch == 1:
            best_val_acc = val_acc
            logger.info("Saving best model checkpoint (Val Acc: %.2f%%) to %s", val_acc * 100.0, checkpoint_path)
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "num_classes": num_classes,
                    "hidden_dim": args.hidden_dim,
                    "nhead": args.nhead,
                    "label_map": label_map.to_dict(),
                    "epoch": epoch,
                    "val_acc": val_acc,
                    "train_acc": train_acc,
                    "model_name": args.model_name,
                    "model_version": args.model_version,
                },
                checkpoint_path,
            )

    logger.info("Training complete. Best Validation Accuracy: %.2f%%", best_val_acc * 100.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SPOTER sign language recognition model")
    parser.add_argument("--train_data", type=str, default="data/train.pt", help="Path to train.pt")
    parser.add_argument("--test_data", type=str, default="data/test.pt", help="Path to test.pt")
    parser.add_argument("--label_map", type=str, default="data/label_map.json", help="Path to label_map.json")
    parser.add_argument("--output_dir", type=str, default="models", help="Directory to save checkpoint")
    parser.add_argument("--model_name", type=str, default="spoter_arsl", help="Model name")
    parser.add_argument("--model_version", type=str, default="v1", help="Model version")
    parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=1, help="Batch size (1 preserves native sequence lengths)")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--optimizer", type=str, default="adamw", choices=["sgd", "adamw"], help="Optimizer type")
    parser.add_argument("--hidden_dim", type=int, default=108, help="Hidden dimension (54 landmarks * 2)")
    parser.add_argument("--nhead", type=int, default=9, help="Number of attention heads")
    parser.add_argument("--num_encoder_layers", type=int, default=6, help="Encoder layers")
    parser.add_argument("--num_decoder_layers", type=int, default=6, help="Decoder layers")
    parser.add_argument("--gaussian_std", type=float, default=0.001, help="Data augmentation gaussian std")
    parser.add_argument("--scheduler_factor", type=float, default=0.5, help="LR scheduler reduction factor")
    parser.add_argument("--scheduler_patience", type=int, default=3, help="LR scheduler patience")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--force_cpu", action="store_true", help="Force CPU even if CUDA is available")
    args = parser.parse_args()

    train(args)
