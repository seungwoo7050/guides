#!/usr/bin/env python3
"""A deterministic event-time fixed-window model with corrections."""

from __future__ import annotations

import hashlib
import json
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

    @property
    def pane_id(self) -> str:
        identity = json.dumps(
            [
                self.key,
                self.window_start.astimezone(UTC).isoformat(),
                self.window_end.astimezone(UTC).isoformat(),
                self.version,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return "pane-" + hashlib.sha256(identity).hexdigest()


def _utc(value: object, *, label: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")
    return value.astimezone(UTC)


def _event(event: object) -> tuple[str, str, datetime, int]:
    if not isinstance(event, Event):
        raise ValueError("event must be an Event")
    if not isinstance(event.event_id, str) or not event.event_id:
        raise ValueError("event_id must be a non-empty string")
    if not isinstance(event.key, str) or not event.key:
        raise ValueError("key must be a non-empty string")
    if not isinstance(event.amount, int) or isinstance(event.amount, bool):
        raise ValueError("amount must be an integer")
    return event.event_id, event.key, _utc(event.occurred_at, label="event time"), event.amount


def floor_window(value: datetime, size: timedelta) -> datetime:
    value = _utc(value, label="event time")
    if not isinstance(size, timedelta):
        raise ValueError("window size must be a timedelta")
    raw_seconds = size.total_seconds()
    if raw_seconds <= 0 or not raw_seconds.is_integer():
        raise ValueError("window size must be positive whole seconds")
    epoch = int(value.timestamp())
    seconds = int(raw_seconds)
    return datetime.fromtimestamp(epoch - epoch % seconds, tz=UTC)


class FixedWindowAggregator:
    def __init__(self, window_size: timedelta, allowed_lateness: timedelta) -> None:
        if not isinstance(window_size, timedelta) or window_size.total_seconds() <= 0:
            raise ValueError("window_size must be a positive timedelta")
        if not window_size.total_seconds().is_integer():
            raise ValueError("window_size must use whole seconds")
        if not isinstance(allowed_lateness, timedelta) or allowed_lateness < timedelta(0):
            raise ValueError("allowed_lateness must be a non-negative timedelta")
        self.window_size = window_size
        self.allowed_lateness = allowed_lateness
        self.watermark = datetime.min.replace(tzinfo=UTC)
        self._seen: dict[str, tuple[str, datetime, int]] = {}
        self._totals: dict[tuple[str, datetime], int] = {}
        self._versions: dict[tuple[str, datetime], int] = {}
        self._on_time_emitted: set[tuple[str, datetime]] = set()

    def add(self, event: Event) -> Emission | None:
        event_id, event_key, occurred_at, amount = _event(event)
        payload = (event_key, occurred_at, amount)
        previous = self._seen.get(event_id)
        if previous is not None:
            if previous != payload:
                raise ValueError(f"conflicting duplicate event_id: {event_id}")
            return None
        self._seen[event_id] = payload
        start = floor_window(occurred_at, self.window_size)
        end = start + self.window_size
        if self.watermark > end + self.allowed_lateness:
            return None
        key = (event_key, start)
        self._totals[key] = self._totals.get(key, 0) + amount
        self._versions[key] = self._versions.get(key, 0) + 1
        completeness = "EARLY" if self.watermark < end else "CORRECTED"
        if completeness == "CORRECTED":
            self._on_time_emitted.add(key)
        return Emission(event_key, start, end, self._totals[key], self._versions[key], completeness)

    def advance_watermark(self, watermark: datetime) -> list[Emission]:
        watermark = _utc(watermark, label="watermark")
        if watermark < self.watermark:
            raise ValueError("watermark must not move backwards")
        self.watermark = watermark
        emissions: list[Emission] = []
        for (key, start), total in sorted(self._totals.items()):
            end = start + self.window_size
            window = (key, start)
            if end <= watermark and window not in self._on_time_emitted:
                self._on_time_emitted.add(window)
                self._versions[window] = self._versions.get(window, 0) + 1
                emissions.append(
                    Emission(key, start, end, total, self._versions[window], "ON_TIME")
                )
        return emissions


def closed_totals(events: Iterable[Event], window_size: timedelta) -> dict[tuple[str, datetime], int]:
    if not isinstance(window_size, timedelta) or window_size.total_seconds() <= 0:
        raise ValueError("window_size must be a positive timedelta")
    if not window_size.total_seconds().is_integer():
        raise ValueError("window_size must use whole seconds")
    result: dict[tuple[str, datetime], int] = {}
    seen: dict[str, tuple[str, datetime, int]] = {}
    for event in events:
        event_id, event_key, occurred_at, amount = _event(event)
        payload = (event_key, occurred_at, amount)
        previous = seen.get(event_id)
        if previous is not None:
            if previous != payload:
                raise ValueError(f"conflicting duplicate event_id: {event_id}")
            continue
        seen[event_id] = payload
        key = (event_key, floor_window(occurred_at, window_size))
        result[key] = result.get(key, 0) + amount
    return result
