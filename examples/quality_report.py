#!/usr/bin/env python3
"""Small quality metrics tied to an explicit grain key."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class QualityReport:
    row_count: int
    distinct_keys: int
    duplicate_keys: tuple[str, ...]
    null_required: int
    latest_event_time: datetime | None

    @property
    def passed(self) -> bool:
        return not self.duplicate_keys and self.null_required == 0


def inspect(
    rows: Iterable[dict[str, Any]],
    *,
    key_field: str,
    required_fields: tuple[str, ...],
    event_time_field: str,
) -> QualityReport:
    materialized = list(rows)
    counts = Counter(str(row.get(key_field)) for row in materialized)
    duplicates = tuple(sorted(key for key, count in counts.items() if count > 1))
    null_required = sum(
        1
        for row in materialized
        for field in required_fields
        if row.get(field) is None
    )
    times = [
        datetime.fromisoformat(str(row[event_time_field]).replace("Z", "+00:00"))
        for row in materialized
        if row.get(event_time_field)
    ]
    latest = max(times) if times else None
    if latest is not None and latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return QualityReport(len(materialized), len(counts), duplicates, null_required, latest)
