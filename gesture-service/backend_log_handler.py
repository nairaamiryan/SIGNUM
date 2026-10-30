import json
import logging
import os
import queue
import sys
import threading
import urllib.request


class BackendLogHandler(logging.Handler):
    """Sends log records to the Next.js backend so every component writes to one log file.

    Configuration (environment / .env):
      BACKEND_LOG_URL   - endpoint of the Next.js log receiver
      SERVICE_API_KEY   - shared service key (x-service-key header)
      MAX_MESSAGE_LEN   - max characters of a forwarded message
    """

    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.url = os.environ.get("BACKEND_LOG_URL", "")
        self.service_key = os.environ.get("SERVICE_API_KEY", "")
        self.max_len = int(os.environ.get("MAX_MESSAGE_LEN", "0") or 0)
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
        if not self.url or not self.service_key or self.max_len <= 0:
            if not self._warned:
                self._warned = True
                print(
                    "BackendLogHandler: BACKEND_LOG_URL, SERVICE_API_KEY or MAX_MESSAGE_LEN "
                    "is not set, logs are not forwarded",
                    file=sys.stderr,
                )
            return
        try:
            message = (self.format(record) or "-")[: self.max_len]
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
        import time

        backend_connected = False
        last_error_time = 0

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
                with urllib.request.urlopen(request, timeout=3) as resp:
                    if not backend_connected:
                        backend_connected = True
                        print(
                            f"[BackendLogHandler] Successfully connected to Next.js backend logs at {self.url} (status: {resp.status})",
                            file=sys.stdout,
                            flush=True,
                        )
            except Exception as exc:
                now = time.time()
                # Rate limit error printing to avoid spamming console
                if not backend_connected or (now - last_error_time > 30):
                    last_error_time = now
                    backend_connected = False
                    print(
                        f"[BackendLogHandler] Unable to deliver log to backend {self.url}: {exc}",
                        file=sys.stderr,
                        flush=True,
                    )
