#!/usr/bin/env python3
"""Behavior checker for exercise 4 (exit 0 pass, 1 reject, 2 cannot run)."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


class ContractFailure(AssertionError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractFailure(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {path}: {error}") from error


def load_submission(submission: Path):
    path = submission / "analysis.py"
    if not submission.is_dir() or not path.is_file():
        raise RuntimeError("--submission must contain analysis.py")
    spec = importlib.util.spec_from_file_location(f"exercise4_submission_{id(submission)}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        raise ContractFailure(f"analysis.py import failed: {type(error).__name__}: {error}") from error
    for name in ("analyze_workload", "analyze_queue", "simulate_priority_inversion"):
        require(callable(getattr(module, name, None)), f"analysis.py must export {name}")
    return module


def check_rta(module, fixture: dict[str, Any]) -> None:
    result = module.analyze_workload(fixture)
    expected = fixture["expected"]
    require(result.get("all_schedulable") is expected["all_schedulable"], "overall schedulability is wrong")
    for name, response in expected["responses"].items():
        item = result.get("tasks", {}).get(name, {})
        require(item.get("response") == response, f"{name} response must be {response}, got {item.get('response')}")
        require(isinstance(item.get("iterations"), list) and item["iterations"], f"{name} iteration evidence is missing")
        require(item["iterations"][-1] == response, f"{name} iteration trace does not reach the result")
        require(item.get("blocking") == next(task["blocking"] for task in fixture["tasks"] if task["name"] == name), f"{name} blocking was omitted")


def check_queue(module, fixture: dict[str, Any]) -> None:
    result = module.analyze_queue(fixture)
    expected = fixture["expected"]
    for key in ("accepted", "dropped", "max_depth", "deadline_misses"):
        require(result.get(key) == expected[key], f"queue {key} mismatch: {result.get(key)!r}")
    require(result["accepted"] + len(result["dropped"]) == len(fixture["arrivals"]), "arrivals silently disappeared")
    require(result["max_depth"] <= fixture["capacity"], "queue exceeded capacity")
    require(isinstance(result.get("timeline"), list) and result["timeline"], "queue pressure trace is missing")


def check_priority_inversion(module, fixture: dict[str, Any]) -> None:
    results = {
        protocol: module.simulate_priority_inversion(fixture, protocol=protocol)
        for protocol in ("none", "inheritance")
    }
    for protocol, expected in fixture["expected"].items():
        result = results[protocol]
        require(result.get("completion", {}).get("high") == expected["high_completion"], f"{protocol} high completion mismatch")
        require(result.get("high_response") == expected["high_response"], f"{protocol} high response mismatch")
        require(result.get("high_deadline_miss") is expected["deadline_miss"], f"{protocol} deadline verdict mismatch")
        trace = result.get("trace")
        require(isinstance(trace, list) and trace, f"{protocol} reference trace is missing")
    none_trace = results["none"]["trace"]
    inherited_trace = results["inheritance"]["trace"]
    require(any(row["running"] == "medium" and row["high_state"] == "BLOCKED" for row in none_trace), "trace does not expose unbounded inversion")
    require(not any(row["running"] == "medium" and row["high_state"] == "BLOCKED" for row in inherited_trace), "inheritance did not boost lock owner")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    submission = Path(args.submission).resolve()
    report: dict[str, Any] = {"exercise": "04-deadline-and-priority-review", "submission": str(submission), "checks": []}
    try:
        if not submission.is_dir() or not (submission / "analysis.py").is_file():
            raise RuntimeError("--submission must name a directory containing analysis.py")
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
        report["checks"].append({"name": "load", "status": "FAIL", "detail": str(error)})
        module = None
        failures += 1
    if module is not None:
        for fixture in fixtures:
            try:
                if fixture["kind"] == "rta":
                    check_rta(module, fixture)
                elif fixture["kind"] == "queue":
                    check_queue(module, fixture)
                elif fixture["kind"] == "priority_inversion":
                    check_priority_inversion(module, fixture)
                else:
                    raise RuntimeError(f"unknown fixture kind: {fixture['kind']}")
            except Exception as error:
                failures += 1
                report["checks"].append(
                    {"name": fixture["name"], "status": "FAIL", "detail": f"{type(error).__name__}: {error}"}
                )
            else:
                report["checks"].append({"name": fixture["name"], "status": "PASS"})
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
