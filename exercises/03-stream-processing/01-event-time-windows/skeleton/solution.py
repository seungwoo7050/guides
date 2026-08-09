from __future__ import annotations


def window_totals(events: list[dict], window_minutes: int) -> list[dict]:
    # TODO: use event time, stable windows and event-id deduplication.
    total = sum(int(event["amount"]) for event in events)
    return [{"key": "all", "window_start": "arrival-time", "total": total}]


def lateness_class(event_time: str, watermark: str, allowed_minutes: int) -> str:
    # TODO: parse aware timestamps and compare the lateness budget.
    return "ON_TIME"
