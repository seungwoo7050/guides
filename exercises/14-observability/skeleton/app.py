from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import TextIO


def create_server(log_stream: TextIO, release: str, ready: bool) -> ThreadingHTTPServer:
    del log_stream, release, ready

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/healthz":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"alive\n")
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)
