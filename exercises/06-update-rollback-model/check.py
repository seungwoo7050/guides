#!/usr/bin/env python3
"""Behavior checker for exercise 6 (0 pass, 1 contract reject, 2 cannot run)."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


class ContractFailure(AssertionError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {path}: {error}") from error


def contains(actual: Any, expected: Any, path: str = "result") -> list[str]:
    errors: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        for key, value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing")
            else:
                errors.extend(contains(actual[key], value, f"{path}.{key}"))
    elif actual != expected:
        errors.append(f"{path}: expected {expected!r}, got {actual!r}")
    return errors


def load_submission(submission: Path):
    path = submission / "model.py"
    if not submission.is_dir() or not path.is_file():
        raise RuntimeError("--submission must contain model.py")
    spec = importlib.util.spec_from_file_location(f"exercise6_submission_{id(submission)}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ContractFailure(f"model.py import failed: {type(error).__name__}: {error}") from error
    if not callable(getattr(module, "run_fixture", None)):
        raise ContractFailure("model.py must export run_fixture(data)")
    return module


def check_fixture(module, fixture: dict[str, Any]) -> None:
    result, trace = module.run_fixture(fixture)
    errors = contains(result, fixture["expected"])
    if errors:
        raise ContractFailure("; ".join(errors))
    if not isinstance(trace, list) or len(trace) != len(fixture["events"]):
        raise ContractFailure("one before/after trace row is required per event")
    metadata = result.get("metadata", {})
    if metadata.get("committed") is not True:
        raise ContractFailure("durable committed metadata evidence is missing")
    if result.get("mode") == "CONFIRMED" and result.get("current") is not None:
        image = result.get("slots", {}).get(result["current"])
        if not isinstance(image, dict) or image.get("confirmed") is not True:
            raise ContractFailure("CONFIRMED mode does not select a confirmed image")
    for row in trace:
        after = row.get("after", {})
        if after.get("mode") == "TRIAL":
            previous = after.get("previous")
            previous_image = after.get("slots", {}).get(previous)
            if previous is None or not isinstance(previous_image, dict) or previous_image.get("confirmed") is not True:
                raise ContractFailure("trial trace did not preserve a confirmed rollback image")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    submission = Path(args.submission).resolve()
    report: dict[str, Any] = {"exercise": "06-update-rollback-model", "submission": str(submission), "checks": []}
    try:
        if not submission.is_dir() or not (submission / "model.py").is_file():
            raise RuntimeError("--submission must name a directory containing model.py")
        fixture_paths = sorted((ROOT / "fixtures").glob("*.json"))
        if not fixture_paths:
            raise RuntimeError("checker fixtures are missing")
        fixtures = [load_json(path) for path in fixture_paths]
    except RuntimeError as error:
        report.update(status="ERROR", error=str(error))
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.as_json else f"ERROR: {error}")
        return 2
    failures = 0
    try:
        module = load_submission(submission)
    except ContractFailure as error:
        failures += 1
        module = None
        report["checks"].append({"name": "load", "status": "FAIL", "detail": str(error)})
    if module is not None:
        for fixture in fixtures:
            name = Path(fixture_paths[len(report["checks"])]).stem
            try:
                check_fixture(module, fixture)
            except Exception as error:
                failures += 1
                report["checks"].append({"name": name, "status": "FAIL", "detail": f"{type(error).__name__}: {error}"})
            else:
                report["checks"].append({"name": name, "status": "PASS"})
    report["status"] = "PASS" if failures == 0 else "FAIL"
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            detail = f" - {item['detail']}" if "detail" in item else ""
            print(f"{item['status']:4} {item['name']}{detail}")
        print(f"CHECK {report['status']}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
