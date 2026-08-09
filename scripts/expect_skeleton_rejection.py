#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from process_runner import CommandSpawnError, run_process

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str, output: str = "") -> None:
    detail = f"\n{output[-3000:]}" if output else ""
    raise SystemExit(f"SKELETON REJECTION ERROR: {message}{detail}")


def run(workspace: str, output_file: Path):
    try:
        result = run_process(
            [
                "npm",
                "run",
                "test:stage01",
                f"--workspace={workspace}",
                "--",
                "--json",
                f"--outputFile={output_file}",
            ],
            cwd=ROOT,
            timeout_seconds=180,
            env={**os.environ, "CI": "1"},
            combine_output=True,
            grace_seconds=5,
        )
    except CommandSpawnError as error:
        fail(str(error))
    if result.timed_out:
        fail(f"{workspace} test timed out; process group을 종료했습니다.", result.stdout)
    return result


def read_json(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"{label} Jest JSON을 읽지 못했습니다: {error}")
    if not isinstance(payload, dict):
        fail(f"{label} Jest JSON이 object가 아닙니다.")
    return payload


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mobile-app-skeleton-reject-") as temporary:
        directory = Path(temporary)
        reference_file = directory / "reference.json"
        reference = run("@field-notes/reference", reference_file)
        if reference.returncode != 0:
            fail(f"reference baseline 실패: exit={reference.returncode}", reference.stdout)
        reference_json = read_json(reference_file, "reference")
        if reference_json.get("success") is not True or reference_json.get("numFailedTests") != 0:
            fail("reference baseline JSON이 pass를 보고하지 않았습니다.")

        skeleton_file = directory / "skeleton.json"
        skeleton = run("@field-notes/skeleton", skeleton_file)
        if skeleton.returncode == 0:
            fail("의도적 Stage 01 TODO가 contract suite를 통과했습니다.")
        skeleton_json = read_json(skeleton_file, "skeleton")
        raw_results = skeleton_json.get("testResults")
        if not isinstance(raw_results, list):
            fail("skeleton Jest JSON testResults가 list가 아닙니다.")
        assertions: list[dict[str, object]] = []
        for suite in raw_results:
            if not isinstance(suite, dict):
                fail("skeleton Jest JSON suite가 object가 아닙니다.")
            raw_assertions = suite.get("assertionResults", [])
            if not isinstance(raw_assertions, list) or not all(
                isinstance(assertion, dict) for assertion in raw_assertions
            ):
                fail("skeleton Jest JSON assertionResults가 object list가 아닙니다.")
            assertions.extend(raw_assertions)
        expected = {
            "Stage 01 learner contract normalizes routes, duplicate intent identity, and dirty back behavior",
            "Stage 01 learner form contract rejects an empty title with an observable error and preserves the draft",
        }
        rejected = {
            str(assertion.get("fullName"))
            for assertion in assertions
            if assertion.get("status") == "failed" and assertion.get("fullName") in expected
        }
        if rejected != expected:
            actual = [
                {"fullName": item.get("fullName"), "status": item.get("status")}
                for item in assertions
            ]
            fail(f"예상한 public behavior 실패가 아닙니다: rejected={sorted(rejected)} actual={actual}")
        if skeleton_json.get("numRuntimeErrorTestSuites") != 0:
            fail("skeleton rejection이 assertion이 아닌 runtime suite 오류를 포함합니다.")
        print(
            "SKELETON REJECTED "
            f"baseline_pass={reference_json.get('numPassedTests')} behavior_failures={len(rejected)}"
        )


if __name__ == "__main__":
    main()
