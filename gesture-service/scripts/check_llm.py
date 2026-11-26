"""
Manual check of the LLM connection (KAN-19).

Run from the gesture-service folder:

    python scripts/check_llm.py            # one real sentence generation
    python scripts/check_llm.py --list     # models available for your API key

Reads GEMINI_API_KEY (and LLM_MODEL, LLM_PROVIDER) from the environment or
from gesture-service/.env. The key is never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_env_file(path: Path) -> None:
    """Minimal .env reader (KEY=VALUE lines); existing variables win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def list_models() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        sys.exit("GEMINI_API_KEY is not set (put it in gesture-service/.env).")
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
        headers={"x-goog-api-key": api_key},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
    names = sorted(
        m["name"].removeprefix("models/")
        for m in data.get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    )
    print("Models that support generateContent (use one as LLM_MODEL):")
    for name in names:
        print(" ", name)


async def check_generation() -> None:
    from gloss_sequence import GlossSequenceProcessor
    from nlp import NLPService, build_provider

    provider = build_provider()
    if provider is None:
        sys.exit("LLM is not configured: set GEMINI_API_KEY in gesture-service/.env.")

    class Prediction:
        def __init__(self, gloss: str, confidence: float) -> None:
            self.gloss = [gloss]
            self.confidence = confidence

    # I - water - want (the Armenian glosses of the label map)
    processor = GlossSequenceProcessor("check")
    processor.add_prediction(Prediction("ԵՍ", 0.9), 0, 800)
    processor.add_prediction(Prediction("ՋՈՒՐ", 0.9), 1500, 2300)
    processor.add_prediction(Prediction("ՈՒԶԵԼ", 0.9), 3000, 3800)
    sequence = processor.close("finalize")
    assert sequence is not None  # three accepted glosses always form a sequence

    print("Provider:", provider.name, "| model:", provider.model)
    print("Glosses :", sequence.gloss_text)
    result = await NLPService(provider).generate(sequence)
    print("Status  :", result.status.value, "| warnings:", result.warnings)
    print("Sentence:", result.text)
    print("Latency :", result.latency_ms, "ms")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the LLM connection.")
    parser.add_argument("--list", action="store_true", help="list models for the API key")
    args = parser.parse_args()
    load_env_file(SERVICE_DIR / ".env")
    if args.list:
        list_models()
    else:
        asyncio.run(check_generation())


if __name__ == "__main__":
    main()
