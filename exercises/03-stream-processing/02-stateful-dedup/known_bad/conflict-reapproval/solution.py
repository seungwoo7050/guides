from __future__ import annotations


def apply_events(events: list[dict], dedup_horizon: int) -> dict:
    if dedup_horizon < 0:
        raise ValueError("negative horizon")
    ordered = sorted(events, key=lambda event: (event["event_time"], event["event_id"]))
    seen = {}
    latest = {}
    stats = {"applied": 0, "duplicate": 0, "stale": 0, "conflict": 0}
    conflicts = []
    for event in ordered:
        event_id = event["event_id"]
        payload = (event["entity_id"], event["version"], event["event_time"], event["operation"], repr(event["value"]))
        if event_id in seen:
            if seen[event_id] == payload:
                stats["duplicate"] += 1
            else:
                stats["conflict"] += 1
                conflicts.append(event_id)
            continue
        seen[event_id] = payload
        previous = latest.get(event["entity_id"])
        if previous and event["version"] < previous["version"]:
            stats["stale"] += 1
            continue
        latest[event["entity_id"]] = {
            "version": event["version"],
            "deleted": event["operation"] == "DELETE",
            "value": None if event["operation"] == "DELETE" else event["value"],
        }
        stats["applied"] += 1
    cutoff = max((event["event_time"] for event in events), default=0) - dedup_horizon
    return {
        "state": latest,
        "stats": stats,
        "conflicts": sorted(set(conflicts)),
        "retained_event_ids": sorted(key for key, payload in seen.items() if payload[2] >= cutoff),
    }
