from __future__ import annotations


def apply_events(events: list[dict], dedup_horizon: int) -> dict:
    return {
        "state": {},
        "stats": {"applied": 0, "duplicate": 0, "stale": 0, "conflict": 0},
        "conflicts": [],
        "retained_event_ids": [],
    }
