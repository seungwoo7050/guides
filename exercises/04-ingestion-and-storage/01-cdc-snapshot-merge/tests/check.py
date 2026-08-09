#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:cdc-snapshot-merge"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        solution = load(Path(sys.argv[1]).resolve())
        snapshot = [
            {"key": "o1", "position": 10, "value": {"status": "NEW"}},
            {"key": "o2", "position": 20, "value": {"status": "PAID"}},
        ]
        changes = [
            {"key": "o1", "position": 12, "operation": "UPDATE", "after": {"status": "PAID"}},
            {"key": "o1", "position": 11, "operation": "UPDATE", "after": {"status": "CANCELLED"}},
            {"key": "o2", "position": 21, "operation": "DELETE", "after": None},
            {"key": "o2", "position": 19, "operation": "UPDATE", "after": {"status": "NEW"}},
            {"key": "o3", "position": 30, "operation": "DELETE", "after": None},
            {"key": "o3", "position": 29, "operation": "INSERT", "after": {"status": "STALE"}},
            {"key": "o3", "position": 31, "operation": "INSERT", "after": {"status": "NEW"}},
            {"key": "o3", "position": 31, "operation": "INSERT", "after": {"status": "NEW"}},
        ]
        expected = {"o1": {"status": "PAID"}, "o3": {"status": "NEW"}}
        assert solution.materialize(snapshot, changes) == expected
        assert solution.materialize(snapshot, list(reversed(changes))) == expected
        delete_only = [
            {"key": "o1", "position": 11, "operation": "DELETE", "after": None},
            {"key": "o1", "position": 9, "operation": "UPDATE", "after": {"status": "STALE"}},
        ]
        assert solution.materialize(snapshot[:1], delete_only) == {}
    except Exception as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    print("OK cdc-snapshot-merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
