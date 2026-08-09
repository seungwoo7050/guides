from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


def _bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _event(record: object) -> tuple[str, str, str, int]:
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    event_id = record.get("event_id")
    sales_date = record.get("sales_date")
    currency = record.get("currency")
    amount = record.get("amount_minor")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event_id must be a non-empty string")
    if not isinstance(sales_date, str) or not sales_date:
        raise ValueError("sales_date must be a non-empty string")
    if not isinstance(currency, str) or not currency:
        raise ValueError("currency must be a non-empty string")
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("amount_minor must be an integer")
    return event_id, sales_date, currency, amount


def aggregate(records: list[dict]) -> list[dict]:
    seen: dict[str, tuple[str, str, int]] = {}
    totals: dict[tuple[str, str], int] = {}
    for raw in records:
        event_id, sales_date, currency, amount = _event(raw)
        payload = (sales_date, currency, amount)
        previous = seen.get(event_id)
        if previous is not None:
            if previous != payload:
                raise ValueError(f"conflicting duplicate event_id: {event_id}")
            continue
        seen[event_id] = payload
        key = (sales_date, currency)
        totals[key] = totals.get(key, 0) + amount
    return [
        {"sales_date": date, "currency": currency, "net_amount_minor": amount}
        for (date, currency), amount in sorted(totals.items())
    ]


def _canonical_rows(rows: list[dict]) -> list[dict]:
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("rows must be a list of objects")
    canonical = json.loads(json.dumps(rows, ensure_ascii=False, allow_nan=False))
    return sorted(canonical, key=lambda row: _bytes(row))


def _verify_snapshot(final: Path, data: bytes, manifest: bytes) -> None:
    if not final.is_dir() or final.is_symlink():
        raise ValueError("snapshot path is not a regular directory")
    data_path = final / "data.json"
    manifest_path = final / "manifest.json"
    if data_path.is_symlink() or manifest_path.is_symlink():
        raise ValueError("snapshot files must not be symlinks")
    if not data_path.is_file() or not manifest_path.is_file():
        raise ValueError("snapshot is incomplete")
    if data_path.read_bytes() != data or manifest_path.read_bytes() != manifest:
        raise ValueError("existing snapshot does not match its content identity")


def publish(root: Path, logical_id: str, rows: list[dict]) -> str:
    if not isinstance(logical_id, str) or not logical_id:
        raise ValueError("logical_id must be a non-empty string")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    canonical_rows = _canonical_rows(rows)
    identity = _bytes({"logical_id": logical_id, "rows": canonical_rows})
    content_id = hashlib.sha256(identity).hexdigest()
    data = _bytes(canonical_rows)
    manifest = _bytes(
        {
            "logical_id": logical_id,
            "content_id": content_id,
            "rows": len(canonical_rows),
            "data_sha256": hashlib.sha256(data).hexdigest(),
        }
    )
    final = root / "snapshots" / content_id
    if final.exists() or final.is_symlink():
        _verify_snapshot(final, data, manifest)
    else:
        staging_parent = root / ".staging"
        staging_parent.mkdir(exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix="run-", dir=staging_parent))
        try:
            (staging / "data.json").write_bytes(data)
            (staging / "manifest.json").write_bytes(manifest)
            _verify_snapshot(staging, data, manifest)
            final.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(staging, final)
            except OSError:
                if not final.exists():
                    raise
                _verify_snapshot(final, data, manifest)
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    descriptor, raw_tmp = tempfile.mkstemp(prefix=".CURRENT-", dir=root)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content_id + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, root / "CURRENT")
    finally:
        tmp.unlink(missing_ok=True)
    return content_id
