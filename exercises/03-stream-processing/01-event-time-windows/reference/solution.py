from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def _parse(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _format(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _window_size(minutes: object) -> int:
    if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
        raise ValueError("window_minutes must be a positive integer")
    return minutes


def _floor(value: datetime, minutes: int) -> datetime:
    seconds = minutes * 60
    epoch_bucket = math.floor(value.timestamp() / seconds) * seconds
    return datetime.fromtimestamp(epoch_bucket, tz=UTC)


def _event(value: object) -> tuple[str, str, datetime, int]:
    if not isinstance(value, dict):
        raise ValueError("event must be an object")
    event_id = value.get("event_id")
    key = value.get("key")
    amount = value.get("amount")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event_id must be a non-empty string")
    if not isinstance(key, str) or not key:
        raise ValueError("key must be a non-empty string")
    if not isinstance(amount, int) or isinstance(amount, bool):
        raise ValueError("amount must be an integer")
    return event_id, key, _parse(value.get("occurred_at")), amount


def window_totals(events: list[dict], window_minutes: int) -> list[dict]:
    minutes = _window_size(window_minutes)
    seen: dict[str, tuple[str, str, int]] = {}
    totals: dict[tuple[str, datetime], int] = {}
    for raw in events:
        event_id, key, occurred_at, amount = _event(raw)
        payload = (key, _format(occurred_at), amount)
        previous = seen.get(event_id)
        if previous is not None:
            if previous != payload:
                raise ValueError(f"conflicting duplicate event_id: {event_id}")
            continue
        seen[event_id] = payload
        start = _floor(occurred_at, minutes)
        total_key = (key, start)
        totals[total_key] = totals.get(total_key, 0) + amount
    return [
        {
            "key": key,
            "window_start": _format(start),
            "window_end": _format(start + timedelta(minutes=minutes)),
            "total": total,
        }
        for (key, start), total in sorted(totals.items())
    ]


def lateness_class(event_time: str, watermark: str, allowed_minutes: int) -> str:
    if not isinstance(allowed_minutes, int) or isinstance(allowed_minutes, bool) or allowed_minutes < 0:
        raise ValueError("allowed_minutes must be a non-negative integer")
    event = _parse(event_time)
    mark = _parse(watermark)
    if mark <= event:
        return "ON_TIME"
    if mark <= event + timedelta(minutes=allowed_minutes):
        return "CORRECTABLE"
    return "DROPPED"
