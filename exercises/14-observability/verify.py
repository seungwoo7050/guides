#!/usr/bin/env python3
from __future__ import annotations

import http.client
import importlib.util
import io
import json
import re
import sys
import threading
from pathlib import Path
from types import ModuleType
from typing import Callable

ROOT = Path(__file__).resolve().parent
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("observability_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(port: int, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    connection.request("GET", path, headers=headers or {})
    response = connection.getresponse()
    body = response.read().decode("utf-8")
    result_headers = {key.lower(): value for key, value in response.getheaders()}
    status = response.status
    connection.close()
    return status, result_headers, body


def run_server(
    module: ModuleType,
    ready: bool,
    checks: Callable[[int, list[str]], None],
) -> tuple[str, list[str]]:
    log_stream = io.StringIO()
    server = module.create_server(log_stream, "release-2026-08-07.1", ready)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    errors: list[str] = []
    try:
        checks(server.server_address[1], errors)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    return log_stream.getvalue(), errors


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "workspace", "reference"}:
        print("사용법: verify.py [skeleton|workspace|reference]", file=sys.stderr)
        return 2
    module = load_module(ROOT / sys.argv[1] / "app.py")
    all_errors: list[str] = []

    def ready_checks(port: int, errors: list[str]) -> None:
        status, _, _ = request(port, "/healthz")
        if status != 200:
            errors.append("healthz는 ready dependency와 무관하게 200이어야 합니다.")
        status, _, _ = request(port, "/readyz")
        if status != 200:
            errors.append("ready 상태의 readyz는 200이어야 합니다.")
        status, headers, _ = request(
            port,
            "/api/items/123",
            {
                "X-Request-ID": "known-request-1",
                "Authorization": "Bearer top-secret-token",
                "Cookie": "session=secret-cookie",
            },
        )
        if status != 200 or headers.get("x-request-id") != "known-request-1":
            errors.append("유효한 request ID를 보존한 사용자 요청이 실패했습니다.")
        status, headers, _ = request(port, "/api/items/456", {"X-Request-ID": "not/allowed/request/id"})
        replacement = headers.get("x-request-id", "")
        if status != 200 or replacement == "not/allowed/request/id" or not REQUEST_ID.fullmatch(replacement):
            errors.append("잘못된 request ID를 안전한 값으로 교체하지 않았습니다.")
        status, _, _ = request(port, "/api/fail")
        if status != 503:
            errors.append("dependency failure 경로는 503이어야 합니다.")
        status, _, metrics = request(port, "/metrics")
        if status != 200:
            errors.append("metrics endpoint가 200이 아닙니다.")
        for required in (
            "http_requests_total",
            "http_request_duration_seconds_sum",
            "http_request_duration_seconds_count",
            'route="/api/items/:id"',
            'release="release-2026-08-07.1"',
        ):
            if required not in metrics:
                errors.append(f"metric 계약이 없습니다: {required}")
        if 'route="/api/items/123"' in metrics or 'route="/api/items/456"' in metrics:
            errors.append("metric label에 concrete item ID가 들어갔습니다.")

    log_text, errors = run_server(module, True, ready_checks)
    all_errors.extend(errors)
    if "top-secret-token" in log_text or "secret-cookie" in log_text:
        all_errors.append("로그에 Authorization 또는 Cookie secret이 노출되었습니다.")
    records: list[dict] = []
    for line in log_text.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            all_errors.append(f"JSON이 아닌 로그입니다: {line!r}")
    if len(records) < 6:
        all_errors.append("각 요청에 대한 구조화 로그가 충분하지 않습니다.")
    required_fields = {"timestamp", "level", "service", "release", "request_id", "event", "method", "route", "status", "duration_ms"}
    for record in records:
        missing = required_fields - set(record)
        if missing:
            all_errors.append(f"로그 필드가 없습니다: {sorted(missing)}")
        if record.get("release") != "release-2026-08-07.1":
            all_errors.append("로그 release 식별자가 다릅니다.")
        if not isinstance(record.get("request_id"), str) or not REQUEST_ID.fullmatch(record["request_id"]):
            all_errors.append("로그 request_id 형식이 올바르지 않습니다.")
        if not isinstance(record.get("duration_ms"), (int, float)) or record["duration_ms"] < 0:
            all_errors.append("로그 duration_ms가 올바르지 않습니다.")
    if not any(record.get("route") == "/api/items/:id" for record in records):
        all_errors.append("로그에도 normalized route가 필요합니다.")

    def not_ready_checks(port: int, errors: list[str]) -> None:
        if request(port, "/healthz")[0] != 200:
            errors.append("dependency 미준비 상태에서도 healthz는 200이어야 합니다.")
        if request(port, "/readyz")[0] != 503:
            errors.append("dependency 미준비 상태의 readyz는 503이어야 합니다.")

    _, errors = run_server(module, False, not_ready_checks)
    all_errors.extend(errors)

    if all_errors:
        print(f"관측성 검사 실패: {len(all_errors)}건", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: health/readiness, structured logs, request ID, redaction과 stable metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
