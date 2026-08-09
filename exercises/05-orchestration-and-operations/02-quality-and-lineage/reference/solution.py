from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

UTC = timezone.utc


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _dataset(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("dataset must be an object")
    return {field: _text(value.get(field), f"dataset.{field}") for field in ("namespace", "name", "snapshot")}


def _parse_time(value: object) -> datetime:
    text = _text(value, "event_time")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("event_time must be timezone-aware")
    return parsed.astimezone(UTC)


def evaluate_and_emit(
    rows: list[dict],
    *,
    run_id: str,
    job_name: str,
    input_dataset: dict,
    output_dataset: dict,
    code_revision: str,
) -> dict:
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("rows must be a list of objects")
    run = _text(run_id, "run_id")
    job = _text(job_name, "job_name")
    revision = _text(code_revision, "code_revision")
    input_identity = _dataset(input_dataset)
    output_identity = _dataset(output_dataset)

    ids = [row.get("id") for row in rows if isinstance(row.get("id"), str) and row.get("id")]
    counts = Counter(ids)
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    null_required = sum(
        1
        for row in rows
        for field in ("id", "event_time", "value")
        if row.get(field) is None or (field == "id" and not isinstance(row.get(field), str)) or (field == "id" and not row.get(field))
    )
    times: list[datetime] = []
    invalid_event_time = 0
    for row in rows:
        if row.get("event_time") is None:
            continue
        try:
            times.append(_parse_time(row["event_time"]))
        except (TypeError, ValueError):
            invalid_event_time += 1
    latest = max(times).isoformat().replace("+00:00", "Z") if times else None
    passed = not duplicates and null_required == 0 and invalid_event_time == 0
    quality = {
        "passed": passed,
        "row_count": len(rows),
        "distinct_keys": len(counts),
        "duplicate_keys": duplicates,
        "null_required": null_required,
        "invalid_event_time": invalid_event_time,
        "latest_event_time": latest,
    }
    lineage = {
        "event_type": "COMPLETE" if passed else "FAIL",
        "run_id": run,
        "job": {"namespace": "guides/data-engineering", "name": job},
        "code_revision": revision,
        "inputs": [input_identity],
        "outputs": [output_identity] if passed else [],
        "attempted_output": output_identity,
        "quality_passed": passed,
    }
    return {"quality": quality, "lineage": lineage}
