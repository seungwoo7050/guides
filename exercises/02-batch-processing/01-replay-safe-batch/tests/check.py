#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

CODE = "GUIDE_SEMANTIC:replay-safe-batch"


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
        records = [
            {"event_id": "e2", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 50},
            {"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 100},
            {"event_id": "e1", "sales_date": "2026-08-09", "currency": "KRW", "amount_minor": 100},
            {"event_id": "e3", "sales_date": "2026-08-09", "currency": "USD", "amount_minor": 7},
        ]
        rows = solution.aggregate(records)
        reverse_rows = solution.aggregate(list(reversed(records)))
        assert rows == reverse_rows
        assert rows == [
            {"sales_date": "2026-08-09", "currency": "KRW", "net_amount_minor": 150},
            {"sales_date": "2026-08-09", "currency": "USD", "net_amount_minor": 7},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = solution.publish(root, "sales/2026-08-09", rows)
            second = solution.publish(root, "sales/2026-08-09", reverse_rows)
            assert first == second
            assert (root / "CURRENT").read_text().strip() == first
            snapshot = root / "snapshots" / first
            assert snapshot.is_dir()
            assert json.loads((snapshot / "data.json").read_text()) == rows
            assert json.loads((snapshot / "manifest.json").read_text())["content_id"] == first
            assert len(list((root / "snapshots").iterdir())) == 1
    except Exception as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    print("OK replay-safe-batch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
