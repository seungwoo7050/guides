from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


def _bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def aggregate(records: list[dict]) -> list[dict]:
    seen: set[str] = set()
    totals: dict[tuple[str, str], int] = {}
    for record in records:
        event_id = str(record["event_id"])
        if event_id in seen:
            continue
        seen.add(event_id)
        key = (str(record["sales_date"]), str(record["currency"]))
        totals[key] = totals.get(key, 0) + int(record["amount_minor"])
    return [
        {"sales_date": date, "currency": currency, "net_amount_minor": amount}
        for (date, currency), amount in sorted(totals.items())
    ]


def publish(root: Path, logical_id: str, rows: list[dict]) -> str:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    content = _bytes(rows)
    content_id = hashlib.sha256(content).hexdigest()
    final = root / "snapshots" / content_id
    if not final.exists():
        staging_parent = root / ".staging"
        staging_parent.mkdir(exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="run-", dir=staging_parent))
        try:
            (staging / "data.json").write_bytes(content)
            (staging / "manifest.json").write_bytes(
                _bytes({"logical_id": logical_id, "content_id": content_id, "rows": len(rows)})
            )
            if len(json.loads((staging / "data.json").read_text())) != len(rows):
                raise ValueError("validation failed")
            final.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(staging, final)
            except OSError:
                if not final.exists():
                    raise
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    tmp = root / ".CURRENT.tmp"
    tmp.write_text(content_id + "\n", encoding="utf-8")
    os.replace(tmp, root / "CURRENT")
    return content_id
