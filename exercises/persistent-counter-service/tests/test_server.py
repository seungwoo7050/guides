from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.server import create_server


# [Implementation 7] HTTP behavior verification
class CounterServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.counter_file = Path(self.temporary.name) / "counter.txt"
        self.server = create_server("127.0.0.1", 0, self.counter_file)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temporary.cleanup()

    def request(self, path: str, method: str = "GET") -> tuple[int, bytes]:
        request = Request(self.base_url + path, method=method)
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()

    def test_health_count_increment_and_restart_persistence(self) -> None:
        self.assertEqual(self.request("/healthz"), (200, b"ok\n"))
        self.assertEqual(json.loads(self.request("/count")[1]), {"count": 0})
        self.assertEqual(json.loads(self.request("/increment", "POST")[1]), {"count": 1})
        self.assertEqual(json.loads(self.request("/increment", "POST")[1]), {"count": 2})
        self.assertEqual(self.counter_file.read_text(encoding="utf-8"), "2\n")

        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.server = create_server("127.0.0.1", 0, self.counter_file)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.assertEqual(json.loads(self.request("/count")[1]), {"count": 2})

    def test_concurrent_increments_are_not_lost(self) -> None:
        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(lambda _: self.request("/increment", "POST"), range(40)))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(json.loads(self.request("/count")[1]), {"count": 40})

    def test_invalid_state_and_unknown_route_have_explicit_errors(self) -> None:
        self.counter_file.write_text("not-an-integer\n", encoding="utf-8")
        status, body = self.request("/count")
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body), {"error": "counter_state_invalid"})
        status, body = self.request("/unknown")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body), {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
