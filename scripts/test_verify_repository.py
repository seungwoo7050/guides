#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Callable

import verify_repository as verifier

SOURCE_SCENARIO = verifier.ROOT / "projects/synthetic-service-security-review/scenario"


def read_json(root: Path, name: str) -> dict:
    return json.loads((root / name).read_text(encoding="utf-8"))


def write_json(root: Path, name: str, value: dict) -> None:
    (root / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def event_rows(root: Path) -> list[dict]:
    return [json.loads(line) for line in (root / "event-log.jsonl").read_text(encoding="utf-8").splitlines() if line]


def write_events(root: Path, rows: list[dict]) -> None:
    (root / "event-log.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def expect_failure(
    suite: Path,
    label: str,
    mutate: Callable[[Path], None],
    expected: str,
) -> None:
    scenario = suite / label
    shutil.copytree(SOURCE_SCENARIO, scenario)
    mutate(scenario)
    verifier.SCENARIO = scenario
    try:
        verifier.check_scenario_integrity()
    except AssertionError as exc:
        if expected not in str(exc):
            raise AssertionError(f"{label}: 기대 오류 {expected!r}, 실제 {exc!r}") from exc
    else:
        raise AssertionError(f"{label}: 손상된 scenario를 허용했습니다.")


def main() -> int:
    baseline = verifier.check_scenario_integrity()
    if baseline != {"assets": 8, "policies": 6, "candidates": 7, "observations": 9, "events": 13, "duplicates": 1}:
        raise AssertionError(f"baseline scenario count가 다릅니다: {baseline}")

    with tempfile.TemporaryDirectory(prefix="cybersecurity-scenario-meta-") as temporary:
        suite = Path(temporary)

        def duplicate_id(root: Path) -> None:
            data = read_json(root, "candidate-findings.json")
            data["candidates"][1]["id"] = data["candidates"][0]["id"]
            write_json(root, "candidate-findings.json", data)

        expect_failure(suite, "duplicate-id", duplicate_id, "중복 ID")

        def broken_reference(root: Path) -> None:
            data = read_json(root, "candidate-findings.json")
            data["candidates"][0]["evidence_refs"].append("OBS-999")
            write_json(root, "candidate-findings.json", data)

        expect_failure(suite, "broken-reference", broken_reference, "알 수 없는 evidence ID OBS-999")

        def bad_timestamp(root: Path) -> None:
            data = read_json(root, "verification-observations.json")
            data["observations"][0]["observed_at"] = "2026-99-99"
            write_json(root, "verification-observations.json", data)

        expect_failure(suite, "bad-timestamp", bad_timestamp, "잘못된 ISO timestamp")

        def event_after_ingest(root: Path) -> None:
            rows = event_rows(root)
            rows[0]["ingest_time"] = "2026-08-08T09:59:59Z"
            write_events(root, rows)

        expect_failure(suite, "event-after-ingest", event_after_ingest, "event_time이 ingest_time보다 늦습니다")

        def broken_duplicate(root: Path) -> None:
            rows = event_rows(root)
            rows[7]["details"]["object_key"] = "synthetic/tenant-42/job-other/input.json"
            write_events(root, rows)

        expect_failure(suite, "broken-duplicate", broken_duplicate, "duplicate payload")

        def broken_deployment_digest(root: Path) -> None:
            data = read_json(root, "release-manifest.json")
            data["artifact"]["declared_digest"] = "sha256:not-in-events"
            write_json(root, "release-manifest.json", data)

        expect_failure(suite, "broken-deployment-digest", broken_deployment_digest, "tag.updated")

        def broken_rollback_digest(root: Path) -> None:
            data = read_json(root, "release-manifest.json")
            data["rollback"]["target_digest"] = "sha256:not-previous"
            write_json(root, "release-manifest.json", data)

        expect_failure(suite, "broken-rollback-digest", broken_rollback_digest, "rollback target_digest")

    verifier.SCENARIO = SOURCE_SCENARIO
    print(
        "REPOSITORY META OK cases=7 "
        "duplicate-id broken-reference bad-timestamp event-after-ingest "
        "broken-duplicate broken-deployment-digest broken-rollback-digest"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        print(f"REPOSITORY META ERROR: {exc}")
        raise SystemExit(1)
