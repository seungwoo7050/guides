#!/usr/bin/env python3
"""Check a field-sensor-node host-model submission.

Exit 0 means the deterministic model checks passed.  It never means that board,
timing, electrical, energy, or hardware-in-the-loop review passed.
Exit 1 means a runnable submission violated the public behaviour contract.
Exit 2 means the checker could not load the submission or its own fixtures.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "fixtures"
EXPECTED_MAP: dict[str, tuple[int, list[str]]] = {
    "S01": (1, ["F07", "F12", "F17", "F26"]),
    "S02": (2, ["F02"]),
    "S03": (3, ["F07", "F09"]),
    "S04": (4, ["F04", "F06"]),
    "S05": (5, ["F12", "F13"]),
    "S06": (6, ["F15", "F16"]),
    "S07": (7, ["F17", "F18"]),
    "S08": (8, ["F23", "F24", "F25"]),
    "S09": (9, ["F26", "F27"]),
    "S10": (10, ["F31", "F34"]),
    "S11": (11, ["F33"]),
    "S12": (12, ["F35"]),
}
REQUIRED_STAGES = {
    "driver",
    "mmio",
    "dma",
    "queue",
    "persistence",
    "upload",
    "power",
    "watchdog",
    "crash",
    "update",
}
HUMAN_REVIEW = [
    {
        "id": "HR01",
        "status": "NOT_TESTED",
        "required_evidence": "target-board probe, raw MMIO/interrupt trace, and debugger-visible DMA ownership",
    },
    {
        "id": "HR02",
        "status": "NOT_TESTED",
        "required_evidence": "measured interrupt latency, deadline response, stack high-water marks, and watchdog window",
    },
    {
        "id": "HR03",
        "status": "NOT_TESTED",
        "required_evidence": "repeatable power-cut, flash-byte, boot-slot, and confirmation-metadata captures",
    },
    {
        "id": "HR04",
        "status": "NOT_TESTED",
        "required_evidence": "sleep/wake current trace, peripheral readback, and energy budget comparison",
    },
    {
        "id": "HR05",
        "status": "NOT_TESTED",
        "required_evidence": "design review of safety state, retry limits, cleanup, and recovery procedure",
    },
]


class InfrastructureError(RuntimeError):
    pass


def _submission_file(path: Path) -> Path:
    candidate = path / "model.py" if path.is_dir() else path
    if not candidate.is_file():
        raise InfrastructureError(f"submission model not found: {candidate}")
    return candidate


def _load_submission(path: Path) -> tuple[ModuleType, Callable[..., Any]]:
    model_path = _submission_file(path)
    spec = importlib.util.spec_from_file_location("field_sensor_submission", model_path)
    if spec is None or spec.loader is None:
        raise InfrastructureError(f"cannot create import spec for {model_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # submission import errors are contract/setup errors
        raise InfrastructureError(f"cannot import {model_path}: {exc}") from exc
    runner = getattr(module, "run_fixture", None)
    if not callable(runner):
        raise InfrastructureError(f"{model_path} must export run_fixture(fixture)")
    return module, runner


def _load_fixtures() -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for path in sorted(FIXTURE_DIR.glob("S*.json")):
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InfrastructureError(f"cannot read fixture {path}: {exc}") from exc
        fixture_id = fixture.get("fixture_id")
        if fixture_id not in EXPECTED_MAP:
            raise InfrastructureError(f"unexpected fixture ID in {path}: {fixture_id!r}")
        scenario, matrix = EXPECTED_MAP[fixture_id]
        if fixture.get("acceptance_scenario") != scenario:
            raise InfrastructureError(f"{fixture_id} does not map to acceptance scenario {scenario}")
        if fixture.get("failure_matrix") != matrix:
            raise InfrastructureError(f"{fixture_id} failure-matrix mapping changed")
        if not fixture.get("required_evidence"):
            raise InfrastructureError(f"{fixture_id} must declare required evidence")
        if not isinstance(fixture.get("events"), list) or not fixture["events"]:
            raise InfrastructureError(f"{fixture_id} has no event sequence")
        if not isinstance(fixture.get("expected"), dict):
            raise InfrastructureError(f"{fixture_id} has no expected result")
        fixtures.append(fixture)
    if {fixture["fixture_id"] for fixture in fixtures} != set(EXPECTED_MAP):
        missing = sorted(set(EXPECTED_MAP) - {fixture["fixture_id"] for fixture in fixtures})
        raise InfrastructureError(f"fixture set is incomplete: missing {missing}")
    return fixtures


def _matches(actual: Any, expected: Any, path: str = "result") -> list[str]:
    failures: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        for key, value in expected.items():
            if key not in actual:
                failures.append(f"{path}.{key}: missing")
            else:
                failures.extend(_matches(actual[key], value, f"{path}.{key}"))
    elif actual != expected:
        failures.append(f"{path}: expected {expected!r}, got {actual!r}")
    return failures


def _decode_run(value: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(value, tuple) or len(value) != 2:
        raise InfrastructureError("run_fixture must return (result_dict, trace_list)")
    result, trace = value
    if not isinstance(result, dict) or not isinstance(trace, list):
        raise InfrastructureError("run_fixture must return (result_dict, trace_list)")
    if any(not isinstance(item, dict) for item in trace):
        raise InfrastructureError("every trace entry must be an object")
    try:
        json.dumps({"result": result, "trace": trace}, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise InfrastructureError(f"result and trace must be JSON serializable: {exc}") from exc
    return result, trace


def _generic_checks(
    fixture: dict[str, Any], result: dict[str, Any], trace: list[dict[str, Any]]
) -> list[str]:
    fixture_id = fixture["fixture_id"]
    failures: list[str] = []
    if result.get("fixture_id") != fixture_id:
        failures.append(f"result.fixture_id must be {fixture_id}")
    if len(trace) != len(fixture["events"]):
        failures.append("trace must contain exactly one entry per input event")
    for index, entry in enumerate(trace, start=1):
        if entry.get("step") != index:
            failures.append(f"trace[{index - 1}].step must be {index}")
        expected_op = fixture["events"][index - 1]["op"] if index <= len(fixture["events"]) else None
        if entry.get("op") != expected_op:
            failures.append(f"trace[{index - 1}].op must be {expected_op}")
        if entry.get("violations"):
            failures.append(f"trace[{index - 1}] reports invariant violations")
        depth = entry.get("event_depth")
        capacity = result.get("event_capacity")
        if not isinstance(depth, int) or not isinstance(capacity, int) or not 0 <= depth <= capacity:
            failures.append(f"trace[{index - 1}] violates the bounded-event-queue contract")

    if result.get("violations"):
        failures.append("result reports invariant violations")
    depth = result.get("event_depth")
    max_depth = result.get("max_event_depth")
    event_capacity = result.get("event_capacity")
    if not all(isinstance(value, int) for value in (depth, max_depth, event_capacity)):
        failures.append("event depth/capacity counters must be integers")
    elif not (0 <= depth <= event_capacity and 0 <= max_depth <= event_capacity):
        failures.append("event queue or its high-water mark exceeded capacity")

    records = result.get("records")
    storage_capacity = result.get("storage_capacity")
    if not isinstance(records, list) or not isinstance(storage_capacity, int):
        failures.append("records and storage_capacity must be reported")
    elif len(records) > storage_capacity:
        failures.append("persistent records exceeded storage capacity")
    elif any(not isinstance(record, dict) or not record.get("integrity") for record in records):
        failures.append("only integral records may be reported as durable")
    elif len({record.get("id") for record in records}) != len(records):
        failures.append("durable record IDs must be unique")

    committed = result.get("committed_ids")
    acked = result.get("acked_ids")
    if not isinstance(committed, list) or not isinstance(acked, list):
        failures.append("committed_ids and acked_ids must be lists")
    elif not set(acked).issubset(set(committed)):
        failures.append("an ACK may only name a committed record")

    owners = result.get("buffer_owners")
    if not isinstance(owners, dict) or any(
        owner not in {"DMA", "QUEUE", "CPU"} for owner in owners.values()
    ):
        failures.append("DMA buffer ownership must be explicit and valid")
    if not isinstance(result.get("evidence"), list) or not result.get("evidence"):
        failures.append("result must expose non-empty event evidence")
    return failures


def _error_payload(message: str) -> dict[str, Any]:
    return {
        "status": "ERROR",
        "automated": {"status": "ERROR", "reason": message},
        "human_review": {
            "status": "NOT_TESTED",
            "items": HUMAN_REVIEW,
            "note": "The checker could not run; no completion claim is available.",
        },
    }


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    automated = payload["automated"]
    print(f"AUTOMATED {automated['status']}")
    if "reason" in automated:
        print(f"  {automated['reason']}")
    for scenario in payload.get("scenarios", []):
        matrix = ",".join(scenario["failure_matrix"])
        print(f"[{scenario['status']}] {scenario['id']} acceptance={scenario['acceptance_scenario']} matrix={matrix}")
        for failure in scenario["failures"]:
            print(f"  - {failure}")
    coverage = payload.get("coverage")
    if coverage:
        print(f"[{coverage['status']}] cumulative stages: {', '.join(coverage['observed'])}")
        if coverage["missing"]:
            print(f"  - missing: {', '.join(coverage['missing'])}")
    review = payload["human_review"]
    print(f"HUMAN_REVIEW {review['status']} (not counted as automated PASS)")
    for item in review["items"]:
        print(f"[{item['status']}] {item['id']}: {item['required_evidence']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path, help="directory containing model.py, or model.py")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable JSON document")
    args = parser.parse_args()

    try:
        fixtures = _load_fixtures()
        _, runner = _load_submission(args.submission)
    except InfrastructureError as exc:
        _emit(_error_payload(str(exc)), args.json)
        return 2

    scenarios: list[dict[str, Any]] = []
    observed_stages: set[str] = set()
    total_checks = 0
    passed_checks = 0
    try:
        for fixture in fixtures:
            fixture_id = fixture["fixture_id"]
            failures: list[str] = []
            try:
                first_result, first_trace = _decode_run(runner(fixture))
                second_result, second_trace = _decode_run(runner(fixture))
            except InfrastructureError:
                raise
            except Exception as exc:
                failures.append(f"run_fixture raised {type(exc).__name__}: {exc}")
                first_result, first_trace = {}, []
                second_result, second_trace = {}, []

            checks = 4
            total_checks += checks
            expected_failures = _matches(first_result, fixture["expected"])
            if not expected_failures:
                passed_checks += 1
            failures.extend(expected_failures)
            if first_result == second_result and first_trace == second_trace:
                passed_checks += 1
            else:
                failures.append("same fixture produced a non-deterministic result or trace")
            generic_failures = _generic_checks(fixture, first_result, first_trace)
            if not generic_failures:
                passed_checks += 1
            failures.extend(generic_failures)
            stages = first_result.get("covered_stages", [])
            if isinstance(stages, list) and all(isinstance(stage, str) for stage in stages):
                passed_checks += 1
                observed_stages.update(stages)
            else:
                failures.append("covered_stages must be a list of strings")
            scenarios.append(
                {
                    "id": fixture_id,
                    "acceptance_scenario": fixture["acceptance_scenario"],
                    "failure_matrix": fixture["failure_matrix"],
                    "required_evidence": fixture["required_evidence"],
                    "status": "PASS" if not failures else "FAIL",
                    "failures": failures,
                }
            )
    except InfrastructureError as exc:
        _emit(_error_payload(str(exc)), args.json)
        return 2

    missing_stages = sorted(REQUIRED_STAGES - observed_stages)
    total_checks += 1
    if not missing_stages:
        passed_checks += 1
    all_pass = all(item["status"] == "PASS" for item in scenarios) and not missing_stages
    payload = {
        "status": "PASS" if all_pass else "FAIL",
        "schema_version": 1,
        "submission": str(args.submission),
        "automated": {
            "status": "PASS" if all_pass else "FAIL",
            "passed_checks": passed_checks,
            "total_checks": total_checks,
            "scope": "deterministic host-state model only",
        },
        "scenarios": scenarios,
        "coverage": {
            "status": "PASS" if not missing_stages else "FAIL",
            "required": sorted(REQUIRED_STAGES),
            "observed": sorted(observed_stages),
            "missing": missing_stages,
        },
        "human_review": {
            "status": "NOT_TESTED",
            "items": HUMAN_REVIEW,
            "note": "These items remain required even when automated.status is PASS.",
        },
    }
    _emit(payload, args.json)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
