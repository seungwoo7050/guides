#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

CODE = "GUIDE_SEMANTIC:backfill-plan"
CONTRACT = "GUIDE_CONTRACT:backfill-plan"
SNAPSHOT_PREFIXES = ("lsn:", "snapshot:", "version:", "etag:", "sha256:")
GIT_REVISION = re.compile(r"^git:[0-9a-fA-F]{7,40}$")
FLOATING_VERSION = re.compile(r"(^|[:/@])(?:latest|current|main|head|tip)($|[:/@])", re.IGNORECASE)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def nonempty_string(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label} must be a non-empty string")
    return value


def object_value(value: object, label: str) -> dict:
    require(isinstance(value, dict) and bool(value), f"{label} must be a non-empty object")
    return value


def parse_time(value: object, label: str) -> datetime:
    text = nonempty_string(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{label} must be ISO-8601") from exc
    require(parsed.tzinfo is not None, f"{label} must be timezone-aware")
    return parsed


def version_map(value: object, label: str) -> dict:
    result = object_value(value, label)
    for key, version in result.items():
        nonempty_string(key, f"{label} key")
        require(
            (isinstance(version, int) and not isinstance(version, bool) and version > 0)
            or (isinstance(version, str) and bool(version.strip())),
            f"{label} values must pin a non-empty version",
        )
        if isinstance(version, str):
            require(
                version == version.strip() and not any(character.isspace() for character in version),
                f"{label}.{key} must be an exact version without whitespace",
            )
            require(
                FLOATING_VERSION.search(version.strip()) is None,
                f"{label}.{key} must not use a floating latest/current/main/head/tip version",
            )
    return result


def pinned_snapshot(value: object, label: str) -> str:
    text = nonempty_string(value, label)
    require(
        text == text.strip() and not any(character.isspace() for character in text),
        f"{label} must be an exact pin without whitespace",
    )
    require(
        any(text.startswith(prefix) and len(text) > len(prefix) for prefix in SNAPSHOT_PREFIXES),
        f"{label} must use one of the pinned prefixes: {', '.join(SNAPSHOT_PREFIXES)}",
    )
    require(
        FLOATING_VERSION.search(text) is None,
        f"{label} must not use a floating latest/current/main/head/tip value",
    )
    return text


def check(plan: object) -> None:
    require(isinstance(plan, dict), "plan must be an object")
    nonempty_string(plan.get("backfill_id"), "backfill_id")
    nonempty_string(plan.get("reason"), "reason")
    nonempty_string(plan.get("owner"), "owner")

    interval = object_value(plan.get("interval"), "interval")
    start = parse_time(interval.get("start"), "interval.start")
    end = parse_time(interval.get("end"), "interval.end")
    require(start < end, "interval start must be before end")
    require(interval.get("semantics") == "[start,end)", "interval semantics must be explicit")

    snapshots = object_value(plan.get("input_snapshots"), "input_snapshots")
    for source, snapshot in snapshots.items():
        nonempty_string(source, "input snapshot source")
        pinned_snapshot(snapshot, f"input snapshot {source}")
    transform_revision = nonempty_string(plan.get("transform_revision"), "transform_revision")
    require(
        GIT_REVISION.fullmatch(transform_revision) is not None,
        "transform_revision must be git:<7-40 hexadecimal commit>",
    )
    version_map(plan.get("schema_versions"), "schema_versions")
    version_map(plan.get("reference_versions"), "reference_versions")

    isolation = object_value(plan.get("isolation"), "isolation")
    require(isolation.get("mode") in {"separate-output", "versioned-partitions"}, "backfill output must be isolated")
    nonempty_string(isolation.get("location"), "isolation.location")
    require(isolation.get("live_writer_conflict") == "forbidden", "live/backfill conflict policy missing")

    canary = object_value(plan.get("canary"), "canary")
    canary_interval = object_value(canary.get("interval"), "canary.interval")
    canary_start = parse_time(canary_interval.get("start"), "canary.interval.start")
    canary_end = parse_time(canary_interval.get("end"), "canary.interval.end")
    require(start <= canary_start < canary_end <= end, "canary interval must be inside the backfill interval")
    require(canary.get("approval_required") is True, "canary approval must be required")

    stop_conditions = plan.get("stop_conditions")
    require(isinstance(stop_conditions, list) and len(stop_conditions) >= 2, "at least two stop conditions required")
    normalized_stops = [nonempty_string(value, "stop condition").strip() for value in stop_conditions]
    require(len(set(normalized_stops)) == len(normalized_stops), "stop conditions must be distinct")

    reconciliation = object_value(plan.get("reconciliation"), "reconciliation")
    nonempty_string(reconciliation.get("count"), "reconciliation.count")
    nonempty_string(reconciliation.get("keys"), "reconciliation.keys")
    aggregates = reconciliation.get("aggregates")
    require(isinstance(aggregates, list) and bool(aggregates), "aggregate reconciliation missing")
    for aggregate in aggregates:
        nonempty_string(aggregate, "reconciliation aggregate")

    publish = object_value(plan.get("publish"), "publish")
    require(publish.get("mode") in {"staged-snapshot-swap", "versioned-promotion"}, "publish must be staged")
    nonempty_string(publish.get("consumer_pointer"), "publish.consumer_pointer")
    require(publish.get("requires_canary_approval") is True, "publish must require canary approval")

    resume = object_value(plan.get("resume"), "resume")
    nonempty_string(resume.get("checkpoint_key"), "resume.checkpoint_key")
    require(resume.get("completed_intervals_are_immutable") is True, "completed interval contract missing")
    rollback = object_value(plan.get("rollback"), "rollback")
    nonempty_string(rollback.get("method"), "rollback.method")
    require(rollback.get("previous_snapshot_recorded") is True, "previous snapshot must be recorded")
    require(plan.get("dry_run") is True, "the repository exercise plan must remain dry_run=true")


def main() -> int:
    try:
        target = Path(sys.argv[1]).resolve()
        plan = json.loads((target / "plan.json").read_text(encoding="utf-8"))
        check(plan)
    except AssertionError as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"{CONTRACT}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("OK backfill-plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
