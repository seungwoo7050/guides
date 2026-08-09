from __future__ import annotations

import json
from collections import Counter, defaultdict


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _event(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("event must be an object")
    event_id = raw.get("event_id")
    entity_id = raw.get("entity_id")
    version = raw.get("version")
    event_time = raw.get("event_time")
    operation = raw.get("operation")
    value = raw.get("value")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event_id must be a non-empty string")
    if not isinstance(entity_id, str) or not entity_id:
        raise ValueError("entity_id must be a non-empty string")
    if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
        raise ValueError("version must be a positive integer")
    if not isinstance(event_time, int) or isinstance(event_time, bool):
        raise ValueError("event_time must be an integer")
    if operation == "DELETE":
        if value is not None:
            raise ValueError("DELETE value must be null")
    elif operation == "UPSERT":
        if not isinstance(value, dict):
            raise ValueError("UPSERT value must be an object")
    else:
        raise ValueError(f"unsupported operation: {operation}")
    return json.loads(
        json.dumps(
            {
                "event_id": event_id,
                "entity_id": entity_id,
                "version": version,
                "event_time": event_time,
                "operation": operation,
                "value": value,
            },
            allow_nan=False,
        )
    )


def _delivery_payload(event: dict) -> str:
    return _canonical({key: value for key, value in event.items() if key != "event_id"})


def _version_payload(event: dict) -> str:
    return _canonical({"operation": event["operation"], "value": event["value"]})


def apply_events(events: list[dict], dedup_horizon: int) -> dict:
    if not isinstance(dedup_horizon, int) or isinstance(dedup_horizon, bool) or dedup_horizon < 0:
        raise ValueError("dedup_horizon must be a non-negative integer")
    if not isinstance(events, list):
        raise ValueError("events must be a list")
    normalized = [_event(raw) for raw in events]

    by_event_id: dict[str, list[dict]] = defaultdict(list)
    for event in normalized:
        by_event_id[event["event_id"]].append(event)

    conflicts: set[str] = set()
    duplicate_count = 0
    safe_events: list[dict] = []
    for event_id, group in by_event_id.items():
        counts = Counter(_delivery_payload(event) for event in group)
        duplicate_count += sum(count - 1 for count in counts.values())
        if len(counts) > 1:
            conflicts.add(event_id)
            continue
        safe_events.append(min(group, key=lambda event: (event["event_time"], _canonical(event))))

    by_version: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for event in safe_events:
        by_version[(event["entity_id"], event["version"])].append(event)

    representatives: list[dict] = []
    for group in by_version.values():
        variants = {_version_payload(event) for event in group}
        if len(variants) > 1:
            conflicts.update(event["event_id"] for event in group)
            continue
        duplicate_count += len(group) - 1
        representatives.append(min(group, key=lambda event: (event["event_time"], event["event_id"])))

    accepted_ids = {
        event["event_id"]
        for event in safe_events
        if event["event_id"] not in conflicts
    }
    latest: dict[str, dict] = {}
    applied = 0
    stale = 0
    for event in sorted(representatives, key=lambda value: (value["event_time"], value["event_id"])):
        if event["event_id"] in conflicts:
            continue
        entity_id = event["entity_id"]
        previous = latest.get(entity_id)
        if previous is not None and event["version"] < previous["version"]:
            stale += 1
            continue
        latest[entity_id] = {
            "version": event["version"],
            "deleted": event["operation"] == "DELETE",
            "value": None if event["operation"] == "DELETE" else event["value"],
        }
        applied += 1

    max_time = max((event["event_time"] for event in normalized), default=0)
    cutoff = max_time - dedup_horizon
    retained = sorted(
        event_id
        for event_id in accepted_ids
        if by_event_id[event_id][0]["event_time"] >= cutoff
    )
    return {
        "state": {key: latest[key] for key in sorted(latest)},
        "stats": {
            "applied": applied,
            "duplicate": duplicate_count,
            "stale": stale,
            "conflict": len(conflicts),
        },
        "conflicts": sorted(conflicts),
        "retained_event_ids": retained,
    }
