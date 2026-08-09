from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - HTTP method hook
        if self.path in {"/", "/ready", "/live"}:
            payload = b"ok\n"
            self.send_response(200)
        else:
            payload = b"not found\n"
            self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format, *_args):
        return


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
