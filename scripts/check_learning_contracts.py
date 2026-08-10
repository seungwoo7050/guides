#!/usr/bin/env python3
"""Run every public lab/capstone checker with positive and negative controls."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Contract:
    name: str
    directory: str
    reference: str
    starter: str
    known_wrong_kind: str
    scope: str = "exercises"


CONTRACTS = (
    Contract("01-image-and-memory-audit", "exercises/01-image-and-memory-audit", "reference/submission.json", "starter/submission.json", "json-files"),
    Contract("02-interrupt-event-path", "exercises/02-interrupt-event-path", "reference/model.py", "starter/model.py", "python-files"),
    Contract("03-sensor-driver-state-machine", "exercises/03-sensor-driver-state-machine", "reference", "starter", "child-directories"),
    Contract("04-deadline-and-priority-review", "exercises/04-deadline-and-priority-review", "reference", "starter", "child-directories"),
    Contract("05-power-loss-persistence", "exercises/05-power-loss-persistence", "reference", "starter", "child-directories"),
    Contract("06-update-rollback-model", "exercises/06-update-rollback-model", "reference", "starter", "child-directories"),
    Contract("field-sensor-node", "capstone/field-sensor-node", "reference", "starter", "python-files", scope="capstone"),
)

EXPECTED_STATUS = {
    0: {"pass"},
    1: {"fail"},
    2: {"error", "interface_error"},
}


class ContractError(RuntimeError):
    pass


def known_wrong_paths(directory: Path, kind: str) -> list[Path]:
    root = directory / "known-wrong"
    if not root.is_dir() or root.is_symlink():
        raise ContractError(f"{directory}: known-wrong directory is missing or unsafe")
    if kind == "json-files":
        paths = sorted(path for path in root.glob("*.json") if path.is_file() and not path.is_symlink())
    elif kind == "python-files":
        paths = sorted(path for path in root.glob("*.py") if path.is_file() and not path.is_symlink())
    elif kind == "child-directories":
        paths = sorted(
            path for path in root.iterdir()
            if path.name != "__pycache__" and path.is_dir() and not path.is_symlink()
        )
    else:
        raise ContractError(f"unknown known-wrong shape: {kind}")
    if not paths:
        raise ContractError(f"{directory}: no known-wrong controls found for {kind}")
    return paths


def parse_json_output(completed: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        detail = completed.stdout.strip() or "<empty stdout>"
        raise ContractError(f"{label}: --json did not emit one JSON object: {detail!r}") from error
    if not isinstance(value, dict):
        raise ContractError(f"{label}: --json result must be an object")
    status = value.get("status")
    if not isinstance(status, str):
        raise ContractError(f"{label}: JSON result has no string status")
    return value


def run_case(
    *,
    python: str,
    checker: Path,
    submission: Path,
    expected_exit: int,
    label: str,
    pycache: Path,
    timeout: float,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPYCACHEPREFIX"] = str(pycache)
    try:
        completed = subprocess.run(
            [python, str(checker), "--submission", str(submission), "--json"],
            cwd=checker.parent,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise ContractError(f"{label}: checker timed out after {timeout:g}s") from error
    report = parse_json_output(completed, label)
    normalized_status = report["status"].strip().lower()
    allowed = EXPECTED_STATUS[expected_exit]
    if completed.returncode != expected_exit:
        raise ContractError(
            f"{label}: exit {completed.returncode}, expected {expected_exit}; "
            f"stderr={completed.stderr.strip()!r}"
        )
    if normalized_status not in allowed:
        raise ContractError(
            f"{label}: status {report['status']!r}, expected one of {sorted(allowed)}"
        )
    return {
        "label": label,
        "exit": completed.returncode,
        "status": report["status"],
        "submission": str(submission),
    }


def selected_contracts(scope: str) -> Iterable[Contract]:
    for contract in CONTRACTS:
        if scope == "all" or contract.scope == scope:
            yield contract


def validate_contract(root: Path, contract: Contract, python: str, pycache: Path, timeout: float) -> list[dict[str, Any]]:
    directory = root / contract.directory
    checker = directory / "check.py"
    if not checker.is_file() or checker.is_symlink():
        raise ContractError(f"{contract.name}: checker is missing or unsafe: {checker}")
    if not os.access(checker, os.X_OK):
        raise ContractError(f"{contract.name}: checker is not executable: {checker}")
    reference = directory / contract.reference
    starter = directory / contract.starter
    if not reference.exists() or reference.is_symlink():
        raise ContractError(f"{contract.name}: reference submission is missing or unsafe: {reference}")
    if not starter.exists() or starter.is_symlink():
        raise ContractError(f"{contract.name}: starter submission is missing or unsafe: {starter}")
    cases = [
        (reference, 0, f"{contract.name}:reference"),
        (starter, 1, f"{contract.name}:starter"),
    ]
    cases.extend((path, 1, f"{contract.name}:known-wrong:{path.name}") for path in known_wrong_paths(directory, contract.known_wrong_kind))
    missing = directory / ".missing-submission-for-contract-check"
    if missing.exists() or missing.is_symlink():
        raise ContractError(f"reserved missing-submission path unexpectedly exists: {missing}")
    cases.append((missing, 2, f"{contract.name}:missing"))
    return [
        run_case(
            python=python,
            checker=checker,
            submission=submission,
            expected_exit=expected_exit,
            label=label,
            pycache=pycache,
            timeout=timeout,
        )
        for submission, expected_exit, label in cases
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--scope", choices=("all", "exercises", "capstone"), default="all")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    root = args.root.resolve()
    report: dict[str, Any] = {"scope": args.scope, "root": str(root), "cases": []}
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        with tempfile.TemporaryDirectory(prefix="embedded-learning-pycache-") as temporary:
            pycache = Path(temporary)
            for contract in selected_contracts(args.scope):
                report["cases"].extend(validate_contract(root, contract, args.python, pycache, args.timeout))
    except (OSError, ContractError) as error:
        report.update(status="FAIL", error=str(error))
        if args.as_json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    report["status"] = "PASS"
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for case in report["cases"]:
            print(f"PASS {case['label']} exit={case['exit']} status={case['status']}")
        print(f"LEARNING CONTRACTS OK scope={args.scope} cases={len(report['cases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
