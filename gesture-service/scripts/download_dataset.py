"""
Download the Slovo MediaPipe Landmarks dataset from Hugging Face.
Dataset: https://huggingface.co/datasets/karinversan/slovo-full-landmarks
"""

import argparse
import logging
import os
from pathlib import Path
from datasets import load_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_dataset")


def download(output_dir: str = "data/slovo-landmarks", max_samples: int | None = None):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading Slovo dataset from HuggingFace (karinversan/slovo-full-landmarks)...")
    dataset = load_dataset("karinversan/slovo-full-landmarks")

    train_data = dataset["train"]
    test_data = dataset.get("test") or dataset.get("validation")

    logger.info("Raw dataset downloaded successfully.")
    logger.info("Train split samples: %d", len(train_data))
    if test_data is not None:
        logger.info("Test split samples: %d", len(test_data))

    if max_samples:
        logger.info("Limiting train samples to %d", max_samples)
        train_data = train_data.select(range(min(max_samples, len(train_data))))
        if test_data is not None:
            test_data = test_data.select(range(min(max_samples // 4, len(test_data))))
        dataset["train"] = train_data
        if test_data is not None:
            dataset["test"] = test_data

    logger.info("Saving dataset to %s ...", output_path)
    dataset.save_to_disk(str(output_path))
    logger.info("Dataset saved successfully to %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download Slovo MediaPipe Landmarks dataset")
    parser.add_argument("--output_dir", type=str, default="data/slovo-landmarks", help="Path to save dataset")
    parser.add_argument("--max_samples", type=int, default=None, help="Optional maximum samples to download/save")
    args = parser.parse_args()

    download(output_dir=args.output_dir, max_samples=args.max_samples)
