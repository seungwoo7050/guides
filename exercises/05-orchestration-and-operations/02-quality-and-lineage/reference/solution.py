from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

UTC = timezone.utc


def _dataset(value: dict) -> dict:
    required = ("namespace", "name", "snapshot")
    if any(not value.get(field) for field in required):
        raise ValueError("dataset requires namespace, name and snapshot")
    return {field: str(value[field]) for field in required}


def _parse_time(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
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
    counts = Counter(str(row.get("id")) for row in rows if row.get("id") is not None)
    duplicates = sorted(key for key, count in counts.items() if count > 1)
    null_required = sum(
        1
        for row in rows
        for field in ("id", "event_time", "value")
        if row.get(field) is None
    )
    times = [_parse_time(row["event_time"]) for row in rows if row.get("event_time") is not None]
    latest = max(times).isoformat().replace("+00:00", "Z") if times else None
    passed = not duplicates and null_required == 0
    quality = {
        "passed": passed,
        "row_count": len(rows),
        "distinct_keys": len(counts),
        "duplicate_keys": duplicates,
        "null_required": null_required,
        "latest_event_time": latest,
    }
    output = _dataset(output_dataset)
    lineage = {
        "event_type": "COMPLETE" if passed else "FAIL",
        "run_id": str(run_id),
        "job": {"namespace": "guides/data-engineering", "name": str(job_name)},
        "code_revision": str(code_revision),
        "inputs": [_dataset(input_dataset)],
        "outputs": [output] if passed else [],
        "attempted_output": output,
        "quality_passed": passed,
    }
    return {"quality": quality, "lineage": lineage}
