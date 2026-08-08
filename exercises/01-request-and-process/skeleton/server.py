#!/usr/bin/env python3
"""README에 적힌 라우팅을 구현할 시작 코드입니다."""

from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.environ.get("APP_HOST", "127.0.0.1")
PORT = int(os.environ.get("APP_PORT", "18081"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - 표준 라이브러리가 정한 메서드 이름입니다.
        # TODO: /와 /healthz 경로 및 404 응답을 구현합니다.
        body = b"skeleton\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        f"수신 주소={HOST}:{server.server_address[1]} pid={os.getpid()}",
        file=sys.stderr,
        flush=True,
    )
    server.serve_forever()
