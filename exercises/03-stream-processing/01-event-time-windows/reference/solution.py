from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _format(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _floor(value: datetime, minutes: int) -> datetime:
    if minutes <= 0:
        raise ValueError("window_minutes must be positive")
    seconds = minutes * 60
    epoch = int(value.timestamp())
    return datetime.fromtimestamp(epoch - epoch % seconds, tz=UTC)


def window_totals(events: list[dict], window_minutes: int) -> list[dict]:
    seen: set[str] = set()
    totals: dict[tuple[str, datetime], int] = {}
    for event in events:
        event_id = str(event["event_id"])
        if event_id in seen:
            continue
        seen.add(event_id)
        occurred_at = _parse(str(event["occurred_at"]))
        start = _floor(occurred_at, window_minutes)
        key = (str(event["key"]), start)
        totals[key] = totals.get(key, 0) + int(event["amount"])
    return [
        {
            "key": key,
            "window_start": _format(start),
            "window_end": _format(start + timedelta(minutes=window_minutes)),
            "total": total,
        }
        for (key, start), total in sorted(totals.items())
    ]


def lateness_class(event_time: str, watermark: str, allowed_minutes: int) -> str:
    if allowed_minutes < 0:
        raise ValueError("allowed_minutes must not be negative")
    event = _parse(event_time)
    mark = _parse(watermark)
    if mark <= event:
        return "ON_TIME"
    if mark <= event + timedelta(minutes=allowed_minutes):
        return "CORRECTABLE"
    return "DROPPED"
