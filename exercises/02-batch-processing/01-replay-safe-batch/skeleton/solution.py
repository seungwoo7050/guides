from __future__ import annotations

import json
from pathlib import Path


def aggregate(records: list[dict]) -> list[dict]:
    # TODO: deduplicate and aggregate by stable keys.
    return [dict(record) for record in records]


def publish(root: Path, logical_id: str, rows: list[dict]) -> str:
    # TODO: stage, validate, publish immutable content, then replace CURRENT.
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "data.json").write_text(json.dumps(rows), encoding="utf-8")
    (root / "CURRENT").write_text(logical_id, encoding="utf-8")
    return logical_id
