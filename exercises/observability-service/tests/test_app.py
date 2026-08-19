from __future__ import annotations

import io
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app import create_server


# [Implementation 8] HTTP telemetry verification
class ObservabilityServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.logs = io.StringIO()
        self.server = create_server(self.logs, "release-42", False)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, path: str, request_id: str | None = None) -> tuple[int, bytes, str]:
        request = Request(self.base_url + path)
        if request_id is not None:
            request.add_header("X-Request-ID", request_id)
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, response.read(), response.headers["X-Request-ID"]
        except HTTPError as error:
            return error.code, error.read(), error.headers["X-Request-ID"]

    def log_records(self) -> list[dict]:
        return [json.loads(line) for line in self.logs.getvalue().splitlines()]

    def test_health_readiness_failure_and_request_ids(self) -> None:
        self.assertEqual(self.request("/healthz", "trace-1"), (200, b"alive\n", "trace-1"))
        status, body, generated = self.request("/readyz", "contains space")
        self.assertEqual((status, body), (503, b"not-ready\n"))
        self.assertRegex(generated, r"^[0-9a-f]{32}$")
        self.assertEqual(self.request("/api/fail", "trace-fail")[:2], (503, b'{"error":"dependency_unavailable"}\n'))
        records = self.log_records()
        self.assertEqual([record["status"] for record in records], [200, 503, 503])
        self.assertTrue(all(record["release"] == "release-42" for record in records))
        self.assertEqual(records[-1]["level"], "error")

    def test_metrics_use_normalized_route_labels(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(lambda index: self.request(f"/api/items/item-{index}"), range(20)))
        self.assertTrue(all(status == 200 for status, _, _ in results))
        status, metrics, _ = self.request("/metrics")
        text = metrics.decode()
        self.assertEqual(status, 200)
        self.assertIn('route="/api/items/:id"', text)
        self.assertIn('status_class="2xx"', text)
        self.assertIn(" 20\n", text)
        self.assertNotIn("item-19", text)
        self.assertNotIn("request_id", text)

    def test_unknown_route_is_bounded_and_logged(self) -> None:
        status, body, request_id = self.request("/unbounded/user/value")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body), {"error": "not_found"})
        record = self.log_records()[-1]
        self.assertEqual(record["route"], "not-found")
        self.assertEqual(record["request_id"], request_id)


if __name__ == "__main__":
    unittest.main()
