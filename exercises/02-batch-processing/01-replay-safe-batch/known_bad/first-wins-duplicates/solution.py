from __future__ import annotations

import hashlib
import json
from pathlib import Path


def aggregate(records: list[dict]) -> list[dict]:
    seen = set()
    totals = {}
    for row in records:
        if row["event_id"] in seen:
            continue
        seen.add(row["event_id"])
        key = (row["sales_date"], row["currency"])
        totals[key] = totals.get(key, 0) + row["amount_minor"]
    return [
        {"sales_date": date, "currency": currency, "net_amount_minor": amount}
        for (date, currency), amount in sorted(totals.items())
    ]


def publish(root: Path, logical_id: str, rows: list[dict]) -> str:
    root = Path(root)
    content = json.dumps(rows, sort_keys=True).encode()
    content_id = hashlib.sha256(content).hexdigest()
    final = root / "snapshots" / content_id
    final.mkdir(parents=True, exist_ok=True)
    (final / "data.json").write_text(json.dumps(rows), encoding="utf-8")
    (final / "manifest.json").write_text(
        json.dumps({"logical_id": logical_id, "content_id": content_id}), encoding="utf-8"
    )
    (root / "CURRENT").write_text(content_id, encoding="utf-8")
    return content_id
