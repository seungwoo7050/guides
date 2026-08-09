#!/usr/bin/env python3
"""A local model of manifest-pinned input and staged snapshot publishing."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def build_input_manifest(files: Iterable[Path]) -> dict[str, Any]:
    entries = []
    for path in sorted((Path(p) for p in files), key=lambda p: p.as_posix()):
        data = path.read_bytes()
        entries.append(
            {
                "path": path.name,
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    manifest_id = hashlib.sha256(canonical_json(entries)).hexdigest()
    return {"manifest_id": manifest_id, "files": entries}


def aggregate(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str], int] = {}
    seen: dict[str, tuple[str, str, int]] = {}
    for record in records:
        if not isinstance(record, Mapping):
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


def _canonical_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("rows must be a list of objects")
    try:
        copied = json.loads(
            json.dumps(rows, ensure_ascii=False, sort_keys=True, allow_nan=False)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("rows must contain JSON values") from exc
    return sorted(copied, key=canonical_json)


def _verify_snapshot(final_dir: Path, content: bytes, manifest: bytes) -> None:
    if not final_dir.is_dir() or final_dir.is_symlink():
        raise ValueError("snapshot path is not a regular directory")
    data_path = final_dir / "data.json"
    manifest_path = final_dir / "manifest.json"
    if data_path.is_symlink() or manifest_path.is_symlink():
        raise ValueError("snapshot files must not be symlinks")
    if not data_path.is_file() or not manifest_path.is_file():
        raise ValueError("snapshot is incomplete")
    if data_path.read_bytes() != content or manifest_path.read_bytes() != manifest:
        raise ValueError("existing snapshot does not match its content identity")


def publish_snapshot(root: Path, logical_id: str, rows: list[dict[str, Any]]) -> str:
    """Publish rows by immutable content ID and atomically replace a pointer.

    Repeating the call with the same logical rows reuses the content directory.
    The consumer-visible CURRENT pointer is changed only after validation.
    """

    if not isinstance(logical_id, str) or not logical_id:
        raise ValueError("logical_id must be a non-empty string")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    canonical_rows = _canonical_rows(rows)
    content = canonical_json(canonical_rows)
    identity = canonical_json({"logical_id": logical_id, "rows": canonical_rows})
    content_id = hashlib.sha256(identity).hexdigest()
    final_dir = root / "snapshots" / content_id
    manifest = canonical_json(
        {
            "logical_id": logical_id,
            "content_id": content_id,
            "row_count": len(canonical_rows),
            "data_sha256": hashlib.sha256(content).hexdigest(),
        }
    )

    if final_dir.exists() or final_dir.is_symlink():
        _verify_snapshot(final_dir, content, manifest)
    else:
        staging_parent = root / ".staging"
        staging_parent.mkdir(exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="snapshot-", dir=staging_parent))
        try:
            (temp_dir / "data.json").write_bytes(content)
            (temp_dir / "manifest.json").write_bytes(manifest)
            # Validation happens before the directory becomes visible.
            _verify_snapshot(temp_dir, content, manifest)
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(temp_dir, final_dir)
            except OSError:
                if not final_dir.exists():
                    raise
                _verify_snapshot(final_dir, content, manifest)
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    descriptor, raw_pointer = tempfile.mkstemp(prefix=".CURRENT-", dir=root)
    pointer_tmp = Path(raw_pointer)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content_id + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pointer_tmp, root / "CURRENT")
    finally:
        pointer_tmp.unlink(missing_ok=True)
    return content_id


def read_current(root: Path) -> list[dict[str, Any]]:
    root = Path(root)
    pointer = root / "CURRENT"
    if not pointer.is_file() or pointer.is_symlink():
        raise ValueError("CURRENT must be a regular file")
    content_id = pointer.read_text(encoding="utf-8").strip()
    if len(content_id) != 64 or any(character not in "0123456789abcdef" for character in content_id):
        raise ValueError("CURRENT content identity is invalid")
    snapshot = root / "snapshots" / content_id
    if not snapshot.is_dir() or snapshot.is_symlink():
        raise ValueError("CURRENT snapshot must be a regular directory")
    data_path = snapshot / "data.json"
    manifest_path = snapshot / "manifest.json"
    if data_path.is_symlink() or manifest_path.is_symlink():
        raise ValueError("snapshot files must not be symlinks")
    try:
        data_bytes = data_path.read_bytes()
        manifest_bytes = manifest_path.read_bytes()
        rows = _canonical_rows(json.loads(data_bytes))
        manifest_value = json.loads(manifest_bytes)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("CURRENT snapshot is unreadable") from exc
    if not isinstance(manifest_value, dict):
        raise ValueError("snapshot manifest must be an object")
    logical_id = manifest_value.get("logical_id")
    if not isinstance(logical_id, str) or not logical_id:
        raise ValueError("snapshot manifest logical_id is invalid")
    canonical_data = canonical_json(rows)
    expected_id = hashlib.sha256(
        canonical_json({"logical_id": logical_id, "rows": rows})
    ).hexdigest()
    expected_manifest = canonical_json(
        {
            "logical_id": logical_id,
            "content_id": expected_id,
            "row_count": len(rows),
            "data_sha256": hashlib.sha256(canonical_data).hexdigest(),
        }
    )
    if content_id != expected_id:
        raise ValueError("CURRENT content identity does not match snapshot data")
    _verify_snapshot(snapshot, canonical_data, expected_manifest)
    return rows
