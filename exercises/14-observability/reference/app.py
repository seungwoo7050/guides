from __future__ import annotations

import json
import re
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TextIO
from urllib.parse import urlsplit

REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class State:
    def __init__(self, log_stream: TextIO, release: str, ready: bool) -> None:
        self.log_stream = log_stream
        self.release = release
        self.ready = ready
        self.lock = threading.Lock()
        self.counts: dict[tuple[str, str, str], int] = defaultdict(int)
        self.duration_seconds: dict[tuple[str, str, str], float] = defaultdict(float)

    def record(self, method: str, route: str, status: int, duration_ms: float) -> None:
        key = (method, route, f"{status // 100}xx")
        with self.lock:
            self.counts[key] += 1
            self.duration_seconds[key] += duration_ms / 1000.0

    def log(self, record: dict[str, object]) -> None:
        with self.lock:
            self.log_stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            self.log_stream.flush()

    def metrics(self) -> str:
        lines = [
            "# HELP http_requests_total Total HTTP requests.",
            "# TYPE http_requests_total counter",
        ]
        with self.lock:
            for key in sorted(self.counts):
                method, route, status_class = key
                labels = f'method="{method}",route="{route}",status_class="{status_class}",release="{self.release}"'
                lines.append(f"http_requests_total{{{labels}}} {self.counts[key]}")
            lines.extend(
                [
                    "# HELP http_request_duration_seconds Request duration in seconds.",
                    "# TYPE http_request_duration_seconds summary",
                ]
            )
            for key in sorted(self.duration_seconds):
                method, route, status_class = key
                labels = f'method="{method}",route="{route}",status_class="{status_class}",release="{self.release}"'
                lines.append(
                    f"http_request_duration_seconds_sum{{{labels}}} "
                    f"{self.duration_seconds[key]:.6f}"
                )
                lines.append(
                    f"http_request_duration_seconds_count{{{labels}}} "
                    f"{self.counts[key]}"
                )
        return "\n".join(lines) + "\n"


def create_server(log_stream: TextIO, release: str, ready: bool) -> ThreadingHTTPServer:
    state = State(log_stream, release, ready)

    class Handler(BaseHTTPRequestHandler):
        server_version = "GuideObservability/1"

        def _request_id(self) -> str:
            candidate = self.headers.get("X-Request-ID", "")
            return candidate if REQUEST_ID.fullmatch(candidate) else uuid.uuid4().hex

        def _respond(self, status: int, body: bytes, content_type: str, request_id: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Request-ID", request_id)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            started = time.monotonic()
            request_id = self._request_id()
            path = urlsplit(self.path).path
            route = "not-found"
            status = 404
            body = b'{"error":"not_found"}\n'
            content_type = "application/json"

            if path == "/healthz":
                route, status, body, content_type = "/healthz", 200, b"alive\n", "text/plain"
            elif path == "/readyz":
                route = "/readyz"
                status = 200 if state.ready else 503
                body = b"ready\n" if state.ready else b"not-ready\n"
                content_type = "text/plain"
            elif re.fullmatch(r"/api/items/[A-Za-z0-9_-]+", path):
                route, status = "/api/items/:id", 200
                item_id = path.rsplit("/", 1)[1]
                body = (json.dumps({"id": item_id}, separators=(",", ":")) + "\n").encode()
            elif path == "/api/fail":
                route, status = "/api/fail", 503
                body = b'{"error":"dependency_unavailable"}\n'
            elif path == "/metrics":
                route, status, content_type = "/metrics", 200, "text/plain; version=0.0.4"
                body = state.metrics().encode()

            self._respond(status, body, content_type, request_id)
            duration_ms = (time.monotonic() - started) * 1000
            state.record("GET", route, status, duration_ms)
            state.log(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "level": "error" if status >= 500 else "info",
                    "service": "guide-observability",
                    "release": state.release,
                    "request_id": request_id,
                    "event": "http_request",
                    "method": "GET",
                    "route": route,
                    "status": status,
                    "duration_ms": round(duration_ms, 3),
                }
            )

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.telemetry_state = state  # type: ignore[attr-defined]
    return server
