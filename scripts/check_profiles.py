#!/usr/bin/env python3
"""Run positive, starter-negative, and verifier meta-profiles."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_EXERCISES = (
    "01-service-classification",
    "02-iaas-failure-domains",
    "03-managed-service-contract",
    "04-faas-event-lifecycle",
    "05-saas-tenant-isolation",
    "06-cost-and-exit",
)
CAPSTONE = ROOT / "projects/multitenant-document-processing-saas"
MODEL = ROOT / "exercises/07-local-cloud-model"
ARTIFACT_VALIDATOR = ROOT / "scripts/check_artifact.py"
MODEL_VALIDATOR = ROOT / "scripts/verify_cloud_model.py"
ERROR_CODE = re.compile(r"ARTIFACT ERROR \[([A-Z][A-Z0-9_]*)\]")


class StrictJSONError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise StrictJSONError(f"duplicate key {key!r}")
        value[key] = item
    return value


def reject_constant(value: str) -> None:
    raise StrictJSONError(f"non-finite number {value!r}")


@dataclass(frozen=True)
class Result:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def environment() -> dict[str, str]:
    value = os.environ.copy()
    value["PYTHONDONTWRITEBYTECODE"] = "1"
    value["PYTHONHASHSEED"] = "0"
    return value


def run(command: list[str], *, timeout: int = 120) -> Result:
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment(),
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"timed out after {timeout}s: {' '.join(command)}") from exc
    return Result(tuple(command), completed.returncode, completed.stdout, completed.stderr)


def fail(label: str, message: str, result: Result | None = None) -> None:
    print(f"[FAIL] {label}: {message}", file=sys.stderr)
    if result is not None:
        if result.stdout:
            sys.stderr.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        print(f"command: {' '.join(result.command)}", file=sys.stderr)
    raise RuntimeError(label)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, StrictJSONError) as exc:
        fail(label, f"cannot load JSON: {exc}")
    if not isinstance(value, dict):
        fail(label, "JSON top level is not an object")
    return value


def artifact_profile(base: Path, label: str) -> None:
    contract_path = base / "contract.json"
    contract = load_json(contract_path, f"{label} contract")
    expected = contract.get("expected_starter_failures")
    if contract.get("validator") != "scripts/check_artifact.py":
        fail(label, "contract validator is not the in-repository artifact checker")
    if (
        not ARTIFACT_VALIDATOR.is_file()
        or not isinstance(expected, list)
        or not expected
        or any(not isinstance(code, str) or not code for code in expected)
    ):
        fail(label, "contract omits a usable validator or expected starter failures")

    reference = run(
        [sys.executable, str(ARTIFACT_VALIDATOR), str(base / "reference"), str(contract_path)]
    )
    if reference.returncode != 0:
        fail(f"{label} reference", "expected exit 0", reference)
    print(f"[PASS] {label} reference")

    starter = run(
        [sys.executable, str(ARTIFACT_VALIDATOR), str(base / "template"), str(contract_path)]
    )
    if starter.returncode != 1:
        fail(
            f"{label} starter",
            f"expected learner-mismatch exit 1, received {starter.returncode}",
            starter,
        )
    actual_codes = sorted(set(ERROR_CODE.findall(starter.output)))
    expected_codes = sorted(set(str(code) for code in expected))
    if actual_codes != expected_codes:
        fail(
            f"{label} starter",
            f"expected error codes {expected_codes}, received {actual_codes}",
            starter,
        )
    print(f"[PASS] {label} starter rejected by {', '.join(actual_codes)}")


def model_profiles() -> None:
    contract = load_json(MODEL / "contract.json", "local model contract")
    check_ids = contract.get("check_ids")
    starter_failures = contract.get("expected_starter_failures")
    if contract.get("validator") != "scripts/verify_cloud_model.py":
        fail("local model contract", "validator is not the in-repository model checker")
    if (
        not MODEL_VALIDATOR.is_file()
        or not isinstance(check_ids, list)
        or check_ids != [f"CM-{number:03d}" for number in range(1, 14)]
        or not isinstance(starter_failures, list)
        or any(not isinstance(code, str) or code not in check_ids for code in starter_failures)
    ):
        fail("local model contract", "invalid validator or check lists")

    cases = (
        ("reference", 0, "PASS", []),
        ("skeleton", 1, "FAIL", starter_failures),
    )
    with tempfile.TemporaryDirectory(prefix="cloud-profile-reports-") as temporary:
        report_root = Path(temporary)
        for profile, expected_exit, expected_result, expected_failures in cases:
            report_path = report_root / f"{profile}.json"
            result = run(
                [
                    sys.executable,
                    str(MODEL_VALIDATOR),
                    "--implementation",
                    str(MODEL / profile / "cloud_model.py"),
                    "--report",
                    str(report_path),
                ]
            )
            label = f"local model {profile}"
            if result.returncode != expected_exit:
                fail(label, f"expected exit {expected_exit}, received {result.returncode}", result)
            report = load_json(report_path, f"{label} report")
            summary = report.get("summary")
            checks = report.get("checks")
            if not isinstance(summary, dict) or not isinstance(checks, list):
                fail(label, "report omits summary or checks", result)
            actual_ids = [item.get("id") for item in checks if isinstance(item, dict)]
            if actual_ids != check_ids:
                fail(label, "report check IDs do not match the declared contract", result)
            if summary.get("result") != expected_result:
                fail(label, f"expected result {expected_result!r}", result)
            if summary.get("failed_ids") != expected_failures or summary.get("errors") != 0:
                fail(
                    label,
                    f"expected failures {expected_failures!r} with zero harness errors",
                    result,
                )
            print(
                f"[PASS] {label}: result={expected_result} "
                f"failed={len(expected_failures)} errors=0"
            )


def meta_test(relative: str, label: str, minimum_tests: int, *, timeout: int = 180) -> None:
    path = ROOT / relative
    if not path.is_file():
        fail(label, f"mandatory test is missing: {relative}")
    result = run([sys.executable, str(path)], timeout=timeout)
    if result.returncode != 0:
        fail(label, f"test process exited {result.returncode}", result)
    match = re.search(r"^Ran ([0-9]+) tests? in ", result.output, flags=re.MULTILINE)
    count = int(match.group(1)) if match else 0
    if count < minimum_tests:
        fail(label, f"expected at least {minimum_tests} executed tests, observed {count}", result)
    print(f"[PASS] {label}: tests={count}")


def main() -> int:
    try:
        for exercise in DOCUMENT_EXERCISES:
            artifact_profile(ROOT / "exercises" / exercise, exercise)
        artifact_profile(CAPSTONE, "capstone")
        model_profiles()
        for relative, label, minimum_tests in (
            ("scripts/test_artifact_verifier.py", "artifact verifier meta-tests", 20),
            ("scripts/test_verify_cloud_model.py", "cloud model verifier meta-tests", 6),
            ("scripts/test_workspace.py", "workspace safety meta-tests", 10),
            ("scripts/test_links.py", "link verifier meta-tests", 10),
            ("scripts/test_source_fingerprint.py", "source fingerprint meta-tests", 6),
        ):
            meta_test(relative, label, minimum_tests)
    except RuntimeError:
        print("PROFILE SUMMARY: FAIL", file=sys.stderr)
        return 1
    print(
        "PROFILE SUMMARY: PASS "
        "(7 references, 7 declared starters, model reference/skeleton, 5 mandatory meta-suites)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
