#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST = os.environ.get("APP_HOST", "0.0.0.0")
PORT = int(os.environ.get("APP_PORT", "8080"))
# [Implementation 1] persistent counter의 소유 파일과 원자 교체 규칙을 먼저 정합니다.
DATA_FILE = Path(os.environ.get("COUNTER_FILE", "/data/counter.txt"))
LOCK = threading.Lock()


def read_count() -> int:
    try:
        return int(DATA_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_count(value: int) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = DATA_FILE.with_suffix(".tmp")
    temp.write_text(f"{value}\n", encoding="utf-8")
    temp.replace(DATA_FILE)


# [Implementation 2] lock 아래 read-modify-write와 public route를 연결합니다.
class Handler(BaseHTTPRequestHandler):
    def reply(self, status: HTTPStatus, payload: dict[str, object] | str) -> None:
        if isinstance(payload, dict):
            body = (json.dumps(payload) + "\n").encode()
            content_type = "application/json"
        else:
            body = (payload + "\n").encode()
            content_type = "text/plain; charset=utf-8"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - 표준 라이브러리가 정한 메서드 이름입니다.
        if self.path == "/healthz":
            self.reply(HTTPStatus.OK, "ok")
        elif self.path == "/count":
            with LOCK:
                self.reply(HTTPStatus.OK, {"count": read_count()})
        else:
            self.reply(HTTPStatus.NOT_FOUND, "요청한 경로를 찾을 수 없습니다.")

    def do_POST(self) -> None:  # noqa: N802 - 표준 라이브러리가 정한 메서드 이름입니다.
        if self.path != "/increment":
            self.reply(HTTPStatus.NOT_FOUND, "요청한 경로를 찾을 수 없습니다.")
            return
        with LOCK:
            value = read_count() + 1
            write_count(value)
            self.reply(HTTPStatus.OK, {"count": value})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"client={self.client_address[0]} {fmt % args}", flush=True)


if __name__ == "__main__":
    print(f"수신 주소={HOST}:{PORT}; 데이터 파일={DATA_FILE}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
