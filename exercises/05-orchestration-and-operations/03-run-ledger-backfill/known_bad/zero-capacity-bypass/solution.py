from __future__ import annotations

from datetime import date, timedelta

ACTIVE = {"PLANNED", "RUNNING", "VALIDATING"}


def plan_backfill(existing_runs, start_date, end_date, policy, max_active):
    if policy not in {"none", "failed", "completed"}:
        raise ValueError("unknown policy")
    if max_active < 0:
        raise ValueError("negative capacity")
    if max_active == 0:
        return []
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if start > end:
        raise ValueError("start after end")
    by_date = {}
    for run in existing_runs:
        by_date.setdefault(run["logical_date"], []).append(run)
    result = []
    current = start
    while current <= end and len(result) < max_active:
        logical_date = current.isoformat()
        runs = sorted(by_date.get(logical_date, []), key=lambda run: run["attempt"])
        if not any(run["status"] in ACTIVE for run in runs):
            latest = runs[-1] if runs else None
            if latest is None or (policy == "failed" and latest["status"] == "FAILED") or (
                policy == "completed" and latest["status"] in {"FAILED", "PUBLISHED", "SUPERSEDED"}
            ):
                result.append({"logical_date": logical_date, "attempt": latest["attempt"] + 1 if latest else 1, "status": "PLANNED", "reason": f"backfill:{policy}"})
        current += timedelta(days=1)
    return result


def transition(run, new_status):
    allowed = {"PLANNED": {"RUNNING", "FAILED"}, "RUNNING": {"VALIDATING", "FAILED"}, "VALIDATING": {"PUBLISHED", "FAILED"}, "PUBLISHED": {"SUPERSEDED"}}
    if new_status not in allowed.get(run["status"], set()):
        raise ValueError("invalid transition")
    return {**run, "status": new_status}
