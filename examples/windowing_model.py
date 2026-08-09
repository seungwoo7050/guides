#!/usr/bin/env python3
"""A deterministic event-time fixed-window model with corrections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

UTC = timezone.utc


@dataclass(frozen=True)
class Event:
    event_id: str
    key: str
    occurred_at: datetime
    amount: int


@dataclass(frozen=True)
class Emission:
    key: str
    window_start: datetime
    window_end: datetime
    total: int
    version: int
    completeness: str


def floor_window(value: datetime, size: timedelta) -> datetime:
    if value.tzinfo is None:
        raise ValueError("event time must be timezone-aware")
    epoch = int(value.timestamp())
    seconds = int(size.total_seconds())
    return datetime.fromtimestamp(epoch - epoch % seconds, tz=UTC)


class FixedWindowAggregator:
    def __init__(self, window_size: timedelta, allowed_lateness: timedelta) -> None:
        self.window_size = window_size
        self.allowed_lateness = allowed_lateness
        self.watermark = datetime.min.replace(tzinfo=UTC)
        self._seen: set[str] = set()
        self._totals: dict[tuple[str, datetime], int] = {}
        self._versions: dict[tuple[str, datetime], int] = {}

    def add(self, event: Event) -> Emission | None:
        if event.event_id in self._seen:
            return None
        self._seen.add(event.event_id)
        start = floor_window(event.occurred_at, self.window_size)
        end = start + self.window_size
        if self.watermark > end + self.allowed_lateness:
            return None
        key = (event.key, start)
        self._totals[key] = self._totals.get(key, 0) + event.amount
        self._versions[key] = self._versions.get(key, 0) + 1
        completeness = "EARLY" if self.watermark < end else "CORRECTED"
        return Emission(event.key, start, end, self._totals[key], self._versions[key], completeness)

    def advance_watermark(self, watermark: datetime) -> list[Emission]:
        if watermark < self.watermark:
            raise ValueError("watermark must not move backwards")
        self.watermark = watermark
        emissions: list[Emission] = []
        for (key, start), total in sorted(self._totals.items()):
            end = start + self.window_size
            if end <= watermark <= end + self.allowed_lateness:
                self._versions[(key, start)] = self._versions.get((key, start), 0) + 1
                emissions.append(
                    Emission(key, start, end, total, self._versions[(key, start)], "ON_TIME")
                )
        return emissions


def closed_totals(events: Iterable[Event], window_size: timedelta) -> dict[tuple[str, datetime], int]:
    result: dict[tuple[str, datetime], int] = {}
    seen: set[str] = set()
    for event in events:
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        key = (event.key, floor_window(event.occurred_at, window_size))
        result[key] = result.get(key, 0) + event.amount
    return result
