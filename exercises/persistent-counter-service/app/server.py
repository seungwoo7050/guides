#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


# [Implementation 1] Counter storage ownership
class CounterStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def read(self) -> int:
        with self._lock:
            return self._read_unlocked()

    def _read_unlocked(self) -> int:
        try:
            value = int(self.path.read_text(encoding="utf-8").strip())
        except FileNotFoundError:
            return 0
        except ValueError as exc:
            raise RuntimeError(f"counter file is invalid: {self.path}") from exc
        if value < 0:
            raise RuntimeError(f"counter file contains a negative value: {self.path}")
        return value

    # [Implementation 1-1] Atomic counter persistence
    def _write_unlocked(self, value: int) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        try:
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(f"{value}\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary.unlink(missing_ok=True)

    # [Implementation 2-1] Serialized increment transaction
    def increment(self) -> int:
        with self._lock:
            value = self._read_unlocked() + 1
            self._write_unlocked(value)
            return value


def create_handler(store: CounterStore) -> type[BaseHTTPRequestHandler]:
    # [Implementation 2] HTTP response and route contract
    class Handler(BaseHTTPRequestHandler):
        server_version = "PersistentCounter/1"

        def _reply(self, status: HTTPStatus, payload: dict[str, Any] | str) -> None:
            if isinstance(payload, dict):
                body = (json.dumps(payload, separators=(",", ":")) + "\n").encode()
                content_type = "application/json"
            else:
                body = (payload + "\n").encode()
                content_type = "text/plain; charset=utf-8"
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler defines this name.
            if self.path == "/healthz":
                self._reply(HTTPStatus.OK, "ok")
                return
            if self.path == "/count":
                try:
                    self._reply(HTTPStatus.OK, {"count": store.read()})
                except RuntimeError:
                    self._reply(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "counter_state_invalid"})
                return
            self._reply(HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler defines this name.
            if self.path != "/increment":
                self._reply(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                self._reply(HTTPStatus.OK, {"count": store.increment()})
            except RuntimeError:
                self._reply(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "counter_state_invalid"})

        def log_message(self, format_string: str, *args: object) -> None:
            print(f"client={self.client_address[0]} {format_string % args}", flush=True)

    return Handler


# [Implementation 3] Server composition and runtime boundary
def create_server(host: str, port: int, counter_file: Path) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), create_handler(CounterStore(counter_file)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the persistent counter HTTP service.")
    parser.add_argument("--host", default=os.environ.get("APP_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("APP_PORT", "8080")))
    parser.add_argument(
        "--counter-file",
        type=Path,
        default=Path(os.environ.get("COUNTER_FILE", "/data/counter.txt")),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = create_server(args.host, args.port, args.counter_file)
    print(
        f"listening={args.host}:{server.server_address[1]} counter_file={args.counter_file}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
