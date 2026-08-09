#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

CODE = "GUIDE_SEMANTIC:replay-safe-batch"
CONTRACT = "GUIDE_CONTRACT:replay-safe-batch"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "aggregate", None)) or not callable(getattr(module, "publish", None)):
        raise TypeError("aggregate and publish are required")
    return module


def check(solution) -> None:
    records = [
        {"event_id": "e2", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 50},
        {"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 100},
        {"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 100},
        {"event_id": "e3", "sales_date": "2026-08-09", "currency": "USD", "amount_minor": 7},
    ]
    original = copy.deepcopy(records)
    rows = solution.aggregate(records)
    reverse_rows = solution.aggregate(list(reversed(records)))
    assert records == original, "aggregate must not mutate input"
    assert rows == reverse_rows, "aggregate must be input-order independent"
    assert rows == [
        {"sales_date": "2026-08-09", "currency": "KRW", "net_amount_minor": 150},
        {"sales_date": "2026-08-09", "currency": "USD", "net_amount_minor": 7},
    ], "deduplicated grouped totals are wrong"

    conflict = [records[1], {**records[1], "amount_minor": 999}]
    for candidate in (conflict, list(reversed(conflict))):
        try:
            solution.aggregate(candidate)
        except ValueError:
            pass
        else:
            raise AssertionError("conflicting duplicate event IDs must be rejected")
    try:
        solution.aggregate([{"event_id": "x", "sales_date": "d", "currency": "KRW", "amount_minor": True}])
    except ValueError:
        pass
    else:
        raise AssertionError("boolean amount must be rejected")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = solution.publish(root, "sales/2026-08-09", list(reversed(rows)))
        second = solution.publish(root, "sales/2026-08-09", rows)
        assert first == second, "same logical snapshot must reuse its identity"
        assert (root / "CURRENT").read_text().strip() == first, "CURRENT must point to the committed snapshot"
        snapshot = root / "snapshots" / first
        assert json.loads((snapshot / "data.json").read_text()) == rows, "snapshot rows must be canonical"
        manifest = json.loads((snapshot / "manifest.json").read_text())
        assert manifest["content_id"] == first and manifest["logical_id"] == "sales/2026-08-09"
        assert len(list((root / "snapshots").iterdir())) == 1, "replay must not create another snapshot"
        other = solution.publish(root, "sales/2026-08-10", rows)
        assert other != first, "different logical intervals must not share a stale manifest"
        assert not any((root / ".staging").iterdir()), "successful publish must clean staging"

        (snapshot / "data.json").write_text("[]\n", encoding="utf-8")
        (root / "CURRENT").write_text("previous\n", encoding="utf-8")
        try:
            solution.publish(root, "sales/2026-08-09", rows)
        except ValueError:
            pass
        else:
            raise AssertionError("corrupt existing snapshot must be rejected")
        assert (root / "CURRENT").read_text().strip() == "previous", (
            "failed validation must not replace the consumer pointer"
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
    print("OK replay-safe-batch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
