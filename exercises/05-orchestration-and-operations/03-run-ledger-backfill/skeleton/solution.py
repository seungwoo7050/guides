from __future__ import annotations


def plan_backfill(existing_runs, start_date, end_date, policy, max_active):
    return []


def transition(run, new_status):
    return {**run, "status": new_status}
