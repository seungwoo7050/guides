#!/usr/bin/env python3
"""A local model of manifest-pinned input and staged snapshot publishing."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterable, Mapping, Any


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


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
    seen: set[str] = set()
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


def publish_snapshot(root: Path, logical_id: str, rows: list[dict[str, Any]]) -> str:
    """Publish rows by immutable content ID and atomically replace a pointer.

    Repeating the call with the same logical rows reuses the content directory.
    The consumer-visible CURRENT pointer is changed only after validation.
    """

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    content = canonical_json(rows)
    content_id = hashlib.sha256(content).hexdigest()
    final_dir = root / "snapshots" / content_id

    if not final_dir.exists():
        staging_parent = root / ".staging"
        staging_parent.mkdir(exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix="snapshot-", dir=staging_parent))
        try:
            (temp_dir / "data.json").write_bytes(content)
            manifest = {
                "logical_id": logical_id,
                "content_id": content_id,
                "row_count": len(rows),
            }
            (temp_dir / "manifest.json").write_bytes(canonical_json(manifest))
            # Validation happens before the directory becomes visible.
            if json.loads((temp_dir / "manifest.json").read_text())["row_count"] != len(rows):
                raise ValueError("row count validation failed")
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(temp_dir, final_dir)
            except OSError:
                if not final_dir.exists():
                    raise
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    pointer_tmp = root / ".CURRENT.tmp"
    pointer_tmp.write_text(content_id + "\n", encoding="utf-8")
    os.replace(pointer_tmp, root / "CURRENT")
    return content_id


def read_current(root: Path) -> list[dict[str, Any]]:
    root = Path(root)
    content_id = (root / "CURRENT").read_text(encoding="utf-8").strip()
    return json.loads((root / "snapshots" / content_id / "data.json").read_text(encoding="utf-8"))
