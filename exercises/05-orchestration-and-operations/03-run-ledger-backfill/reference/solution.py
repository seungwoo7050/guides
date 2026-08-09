from __future__ import annotations

from datetime import date, timedelta

ALLOWED = {
    "PLANNED": {"RUNNING", "FAILED"},
    "RUNNING": {"VALIDATING", "FAILED"},
    "VALIDATING": {"PUBLISHED", "FAILED"},
    "PUBLISHED": {"SUPERSEDED"},
    "FAILED": set(),
    "SUPERSEDED": set(),
}
ACTIVE = {"PLANNED", "RUNNING", "VALIDATING"}
TERMINAL = {"PUBLISHED", "FAILED", "SUPERSEDED"}
POLICIES = {"none", "failed", "completed"}


def _date(value: object, label: str) -> date:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be an ISO date") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD")
    return parsed


def _run(raw: object) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("run must be an object")
    logical_date = raw.get("logical_date")
    _date(logical_date, "logical_date")
    attempt = raw.get("attempt")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt <= 0:
        raise ValueError("attempt must be a positive integer")
    status = raw.get("status")
    if status not in ALLOWED:
        raise ValueError(f"unknown status: {status}")
    return {**raw, "logical_date": logical_date, "attempt": attempt, "status": status}


def _capacity(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("max_active must be a non-negative integer")
    return value


def plan_backfill(
    existing_runs: list[dict],
    start_date: str,
    end_date: str,
    policy: str,
    max_active: int,
) -> list[dict]:
    start = _date(start_date, "start_date")
    end = _date(end_date, "end_date")
    if start > end:
        raise ValueError("start_date must not be after end_date")
    if policy not in POLICIES:
        raise ValueError(f"unknown policy: {policy}")
    capacity = _capacity(max_active)
    if not isinstance(existing_runs, list):
        raise ValueError("existing_runs must be a list")

    by_date: dict[str, list[dict]] = {}
    identities: set[tuple[str, int]] = set()
    for raw in existing_runs:
        run = _run(raw)
        identity = (run["logical_date"], run["attempt"])
        if identity in identities:
            raise ValueError(f"duplicate run identity: {identity[0]} attempt {identity[1]}")
        identities.add(identity)
        by_date.setdefault(run["logical_date"], []).append(run)
    if capacity == 0:
        return []

    plans: list[dict] = []
    current = start
    while current <= end:
        logical_date = current.isoformat()
        runs = by_date.get(logical_date, [])
        if any(run["status"] in ACTIVE for run in runs):
            current += timedelta(days=1)
            continue
        latest = max(runs, key=lambda run: run["attempt"], default=None)
        create = latest is None
        if latest is not None and policy == "failed":
            create = latest["status"] == "FAILED"
        elif latest is not None and policy == "completed":
            create = latest["status"] in TERMINAL
        elif latest is not None and policy == "none":
            create = False
        if create:
            plans.append(
                {
                    "logical_date": logical_date,
                    "attempt": latest["attempt"] + 1 if latest else 1,
                    "status": "PLANNED",
                    "reason": f"backfill:{policy}",
                }
            )
            if len(plans) == capacity:
                break
        current += timedelta(days=1)
    return plans


def transition(run: dict, new_status: str) -> dict:
    current = _run(run)
    if new_status not in ALLOWED[current["status"]]:
        raise ValueError(f"invalid transition: {current['status']}->{new_status}")
    return {**current, "status": new_status}
