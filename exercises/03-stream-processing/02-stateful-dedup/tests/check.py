#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import itertools
import random
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:stateful-dedup"
CONTRACT = "GUIDE_CONTRACT:stateful-dedup"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "apply_events", None)):
        raise TypeError("apply_events is required")
    return module


def expect_value_error(call, message: str) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def check(solution) -> None:
    first = {"event_id": "e1", "entity_id": "o1", "version": 1, "event_time": 10, "operation": "UPSERT", "value": {"status": "NEW"}}
    events = [
        first,
        copy.deepcopy(first),
        {"event_id": "e2", "entity_id": "o1", "version": 3, "event_time": 30, "operation": "DELETE", "value": None},
        {"event_id": "e3", "entity_id": "o1", "version": 2, "event_time": 40, "operation": "UPSERT", "value": {"status": "PAID"}},
    ]
    original = copy.deepcopy(events)
    out = solution.apply_events(events, 100)
    assert events == original, "apply_events must not mutate input"
    assert "o1" in out.get("state", {}), "latest entity state is missing"
    assert out["state"]["o1"] == {"version": 3, "deleted": True, "value": None}
    assert out["stats"]["duplicate"] == 1 and out["stats"]["stale"] == 1

    a = {"event_id": "collision", "entity_id": "o2", "version": 1, "event_time": 50, "operation": "UPSERT", "value": {"x": 1}}
    b = {**a, "value": {"x": 2}}
    expected_conflict = None
    for candidate in set(itertools.permutations(("a", "b", "a"))):
        values = [a if name == "a" else b for name in candidate]
        actual = solution.apply_events(values, 100)
        if expected_conflict is None:
            expected_conflict = actual
        assert actual == expected_conflict, "same-ID conflict result must not depend on input order"
        assert "o2" not in actual["state"], "conflicted event ID must not update entity state"
        assert actual["conflicts"] == ["collision"] and actual["stats"]["conflict"] == 1
        assert "collision" not in actual["retained_event_ids"], "conflicted ID must not re-enter dedup state"

    version_conflict = [
        {"event_id": "base", "entity_id": "o3", "version": 1, "event_time": 1, "operation": "UPSERT", "value": {"x": 0}},
        {"event_id": "va", "entity_id": "o3", "version": 2, "event_time": 2, "operation": "UPSERT", "value": {"x": 1}},
        {"event_id": "vb", "entity_id": "o3", "version": 2, "event_time": 3, "operation": "UPSERT", "value": {"x": 2}},
    ]
    for candidate in (version_conflict, list(reversed(version_conflict))):
        actual = solution.apply_events(candidate, 100)
        assert actual["state"]["o3"]["version"] == 1, "ambiguous higher version must not win"
        assert actual["conflicts"] == ["va", "vb"]

    unordered = [
        {"event_id": f"u{i}", "entity_id": "o4", "version": i, "event_time": 100 - i, "operation": "UPSERT", "value": {"v": i}}
        for i in range(1, 6)
    ]
    expected_state = solution.apply_events(unordered, 1000)["state"]
    random.Random(2).shuffle(unordered)
    assert solution.apply_events(unordered, 1000)["state"] == expected_state
    assert expected_state["o4"]["version"] == 5

    horizon = [
        {"event_id": "old", "entity_id": "o5", "version": 1, "event_time": 89, "operation": "UPSERT", "value": {"v": 1}},
        {"event_id": "cutoff", "entity_id": "o5", "version": 2, "event_time": 90, "operation": "UPSERT", "value": {"v": 2}},
        {"event_id": "new", "entity_id": "o5", "version": 3, "event_time": 100, "operation": "UPSERT", "value": {"v": 3}},
    ]
    actual = solution.apply_events(horizon, 10)
    assert actual["retained_event_ids"] == ["cutoff", "new"], "horizon cutoff must be inclusive"
    assert actual["state"]["o5"]["version"] == 3

    expect_value_error(lambda: solution.apply_events([], -1), "negative horizon must fail on empty input")
    expect_value_error(lambda: solution.apply_events([], True), "boolean horizon must fail")
    expect_value_error(
        lambda: solution.apply_events([
            {"event_id": "x", "entity_id": "o", "version": 1, "event_time": 1, "operation": "BAD", "value": None}
        ], 1),
        "unknown operation must fail",
    )


def main() -> int:
    try:
        solution = load(Path(sys.argv[1]).resolve())
        check(solution)
    except AssertionError as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"{CONTRACT}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("OK stateful-dedup")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
