"""Non-blocking persistence client forwarding gestures and captions to the Next.js API."""

from __future__ import annotations

import json
import logging
import os
import queue
import threading
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger("gesture-service.persistence")


def resolve_backend_base_url() -> str:
    """Resolve the Next.js backend base URL from BACKEND_BASE_URL or BACKEND_LOG_URL."""
    explicit = os.environ.get("BACKEND_BASE_URL", "").strip().rstrip("/")
    if explicit:
        return explicit

    log_url = os.environ.get("BACKEND_LOG_URL", "").strip()
    suffix = "/api/internal/logs"
    if log_url.endswith(suffix):
        return log_url[: -len(suffix)].rstrip("/")
    return ""


class BackendPersistenceClient:
    """Forwards recognized gestures and Armenian captions to the Next.js internal API
    so PostgreSQL stays in sync with the real-time WebSocket recognition pipeline."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        service_key: Optional[str] = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else resolve_backend_base_url()).rstrip(
            "/"
        )
        self.service_key = (
            service_key if service_key is not None else os.environ.get("SERVICE_API_KEY", "")
        )
        self._queue: queue.Queue[tuple[str, dict]] = queue.Queue(maxsize=500)
        self._worker_started = False
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.service_key)

    def _ensure_worker(self) -> None:
        if self._worker_started:
            return
        with self._lock:
            if not self._worker_started:
                self._worker_started = True
                threading.Thread(target=self._worker, daemon=True).start()

    def _enqueue(self, path: str, payload: dict) -> None:
        if not self.enabled:
            return
        self._ensure_worker()
        try:
            self._queue.put_nowait((path, payload))
        except queue.Full:
            logger.debug("Persistence queue full; dropping %s", path)

    def record_gesture(self, session_id: str, gloss: str, confidence: float) -> None:
        """Queue a recognized gesture for persistence under the given session."""
        if not session_id or not gloss:
            return
        self._enqueue(
            f"/api/internal/sessions/{session_id}/gestures",
            {
                "gloss": gloss,
                "confidence": max(0.0, min(1.0, float(confidence))),
            },
        )

    def record_caption(
        self,
        session_id: str,
        text: str,
        glosses: list[str],
        confidence: Optional[float] = None,
    ) -> None:
        """Queue a finalized Armenian caption for persistence under the given session."""
        if not session_id or not text:
            return
        payload: dict = {
            "text": text,
            "glosses": list(glosses),
        }
        if confidence is not None:
            payload["confidence"] = max(0.0, min(1.0, float(confidence)))
        self._enqueue(f"/api/internal/sessions/{session_id}/captions", payload)

    def _worker(self) -> None:
        while True:
            path, payload = self._queue.get()
            url = f"{self.base_url}{path}"
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "x-service-key": self.service_key,
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=3):
                    pass
            except urllib.error.HTTPError as exc:
                # 404 is expected for unauthenticated/guest WebSocket sessions
                # that were not registered in PostgreSQL.
                if exc.code == 404:
                    logger.debug("Session not persisted in backend (%s): 404", path)
                else:
                    logger.warning("Backend persistence %s failed with HTTP %s", path, exc.code)
            except Exception as exc:
                logger.debug("Backend persistence %s skipped: %s", path, exc)
