import json
import logging
import os
import queue
import sys
import threading
import urllib.request

DEFAULT_URL = "http://localhost:3000/api/internal/logs"
MAX_MESSAGE_LEN = 2000


class BackendLogHandler(logging.Handler):
    """Sends log records to the Next.js backend so every component writes to one log file."""

    def __init__(self, url=None, service_key=None, level=logging.INFO):
        super().__init__(level)
        self.url = url or os.environ.get("BACKEND_LOG_URL", DEFAULT_URL)
        self.service_key = service_key or os.environ.get("SERVICE_API_KEY", "")
        self._queue = queue.Queue(maxsize=1000)
        self._warned = False
        threading.Thread(target=self._worker, daemon=True).start()

    @staticmethod
    def _map_level(levelno):
        if levelno >= logging.ERROR:
            return "ERROR"
        if levelno >= logging.WARNING:
            return "WARN"
        if levelno >= logging.INFO:
            return "INFO"
        return "DEBUG"

    def emit(self, record):
        if not self.service_key:
            if not self._warned:
                self._warned = True
                print("BackendLogHandler: SERVICE_API_KEY is not set, logs are not forwarded", file=sys.stderr)
            return
        try:
            message = (self.format(record) or "-")[:MAX_MESSAGE_LEN]
            session_id = getattr(record, "session_id", None)
            payload = {
                "level": self._map_level(record.levelno),
                "message": message,
                "audit": bool(getattr(record, "audit", False)),
                "sessionId": str(session_id) if session_id else None,
            }
            self._queue.put_nowait(payload)
        except Exception:
            pass  # never let logging break the service

    def _worker(self):
        while True:
            payload = self._queue.get()
            try:
                request = urllib.request.Request(
                    self.url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "x-service-key": self.service_key,
                    },
                    method="POST",
                )
                urllib.request.urlopen(request, timeout=3).close()
            except Exception:
                pass  # backend unavailable: drop the line, do not crash
