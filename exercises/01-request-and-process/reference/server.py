#!/usr/bin/env python3
"""요청 경로와 프로세스 종료를 관찰하기 위한 작은 HTTP 서버입니다."""

from __future__ import annotations

import json
import os
import signal
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import NoReturn


HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "18081"))


class Handler(BaseHTTPRequestHandler):
    server_version = "web-infra-exercise/1.0"

    def _write(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - 표준 라이브러리가 정한 메서드 이름입니다.
        print(
            f"method=GET path={self.path} client={self.client_address[0]}",
            file=sys.stderr,
            flush=True,
        )

        if self.path == "/healthz":
            self._write(HTTPStatus.OK, b"ok\n", "text/plain; charset=utf-8")
            return

        if self.path == "/":
            payload = json.dumps(
                {
                    "status": "running",
                    "pid": os.getpid(),
                    "listen": f"{HOST}:{self.server.server_port}",
                },
                ensure_ascii=False,
            ).encode("utf-8") + b"\n"
            self._write(HTTPStatus.OK, payload, "application/json; charset=utf-8")
            return

        self._write(
            HTTPStatus.NOT_FOUND,
            "요청한 경로를 찾을 수 없습니다.\n".encode(),
            "text/plain; charset=utf-8",
        )

    def log_message(self, format: str, *args: object) -> None:
        # 실습에서는 do_GET에서 정해진 형식의 로그 한 줄을 남깁니다.
        return


def main() -> NoReturn:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    actual_port = httpd.server_address[1]
    httpd.timeout = 0.2
    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        print("종료 신호를 받았습니다.", file=sys.stderr, flush=True)
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    print(
        f"수신 주소={HOST}:{actual_port} pid={os.getpid()}",
        file=sys.stderr,
        flush=True,
    )
    while not stopping:
        httpd.handle_request()
    httpd.server_close()
    print("서버를 종료했습니다.", file=sys.stderr, flush=True)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
