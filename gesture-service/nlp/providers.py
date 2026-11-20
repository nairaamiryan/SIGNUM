"""
LLM providers for the NLP layer (KAN-19).

The NLP layer talks to a language model only through the small `LLMProvider`
interface below, so the provider (Gemini, Claude, GPT, ...) can be replaced
by writing one new class and changing `LLM_PROVIDER`; the gesture
classification pipeline is never touched.

GeminiProvider calls the Gemini REST API with the standard library only
(no extra dependency to install or pin).
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Callable, Mapping, Optional, Protocol

from constants import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    LLM_MAX_RETRIES,
    LLM_TEMPERATURE,
)

logger = logging.getLogger("gesture-service.nlp.providers")

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
_RETRY_STATUSES = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """A provider failure. `code` is a short machine-readable reason:
    timeout, network, rate_limited, http_error, blocked, bad_response."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


class LLMProvider(Protocol):
    """What the NLP layer needs from any language model."""

    name: str
    model: str

    def generate(self, system: str, user: str) -> str:
        """Return the model's raw text answer (a JSON string, see prompt.py).
        Raises LLMError on any failure."""
        ...


# transport(url, headers, body, timeout_seconds) -> (http_status, response_bytes)
Transport = Callable[[str, Mapping[str, str], bytes, float], tuple[int, bytes]]


def _urllib_transport(
    url: str, headers: Mapping[str, str], body: bytes, timeout: float
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_LLM_MODEL,
        timeout: float = DEFAULT_LLM_TIMEOUT_SECONDS,
        max_retries: int = LLM_MAX_RETRIES,
        transport: Optional[Transport] = None,
        retry_delay: float = 1.0,
    ) -> None:
        if not api_key:
            raise ValueError("GeminiProvider needs an API key")
        self._api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._transport = transport or _urllib_transport
        self._retry_delay = retry_delay

    def generate(self, system: str, user: str) -> str:
        body = json.dumps(
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "temperature": LLM_TEMPERATURE,
                    "responseMimeType": "application/json",
                },
            }
        ).encode("utf-8")
        url = f"{GEMINI_BASE_URL}/{self.model}:generateContent"
        # The key travels in a header, never in the URL, so it cannot leak into logs.
        headers = {"x-goog-api-key": self._api_key, "Content-Type": "application/json"}

        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                status, raw = self._transport(url, headers, body, self.timeout)
            except (TimeoutError, socket.timeout) as exc:
                error = LLMError("timeout", "request timed out")
                if attempt < attempts:
                    time.sleep(self._retry_delay)
                    continue
                raise error from exc
            except urllib.error.URLError as exc:
                if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                    error = LLMError("timeout", "request timed out")
                else:
                    error = LLMError("network", "could not reach the LLM service")
                if attempt < attempts:
                    time.sleep(self._retry_delay)
                    continue
                raise error from exc

            if status in _RETRY_STATUSES and attempt < attempts:
                logger.warning("Gemini returned HTTP %d, retrying (%d/%d)", status, attempt, attempts)
                time.sleep(self._retry_delay)
                continue
            if status == 429:
                raise LLMError("rate_limited", "HTTP 429")
            if status >= 400:
                raise LLMError("http_error", f"HTTP {status}")
            return self._extract_text(raw)

        raise LLMError("network", "no attempt was made")  # unreachable safeguard

    @staticmethod
    def _extract_text(raw: bytes) -> str:
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise LLMError("bad_response", "response is not JSON") from exc

        feedback = data.get("promptFeedback") or {}
        if feedback.get("blockReason"):
            raise LLMError("blocked", str(feedback["blockReason"]))

        candidates = data.get("candidates") or []
        if not candidates:
            raise LLMError("bad_response", "no candidates")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        texts = [p["text"] for p in parts if isinstance(p.get("text"), str) and not p.get("thought")]
        if not texts:
            raise LLMError("bad_response", f"empty answer (finishReason={candidates[0].get('finishReason')})")
        return "".join(texts)


def build_provider(env: Optional[Mapping[str, str]] = None) -> Optional[LLMProvider]:
    """Create the provider selected by the environment, or None when the NLP
    layer is not configured (the service then falls back to plain glosses)."""
    env = os.environ if env is None else env
    name = (env.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER) or "").strip().lower()

    if name in ("", "none", "off"):
        logger.warning("LLM_PROVIDER is disabled; sentences will fall back to plain glosses.")
        return None

    if name == "gemini":
        api_key = (env.get("GEMINI_API_KEY") or "").strip()
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set; sentences will fall back to plain glosses.")
            return None
        model = (env.get("LLM_MODEL") or DEFAULT_LLM_MODEL).strip()
        try:
            timeout = float(env.get("LLM_TIMEOUT_SECONDS") or DEFAULT_LLM_TIMEOUT_SECONDS)
        except ValueError:
            timeout = DEFAULT_LLM_TIMEOUT_SECONDS
        logger.info("NLP layer uses Gemini model '%s'", model, extra={"audit": True})
        return GeminiProvider(api_key=api_key, model=model, timeout=timeout)

    logger.warning("Unknown LLM_PROVIDER '%s'; sentences will fall back to plain glosses.", name)
    return None
