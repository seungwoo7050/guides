#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


# [Implementation 1] Action schema
@dataclass(frozen=True)
class Action:
    id: str
    severity: str
    evidence: str
    owner: str
    deadline: str
    verification: str
    rollback: str


def action(
    action_id: str,
    severity: str,
    evidence: str,
    owner: str,
    as_of: date,
    verification: str,
    rollback: str,
) -> Action:
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"unsupported severity: {severity}")
    deadline_days = {"critical": 7, "high": 14, "medium": 30, "low": 60}[severity]
    return Action(
        id=action_id,
        severity=severity,
        evidence=evidence,
        owner=owner,
        deadline=(as_of + timedelta(days=deadline_days)).isoformat(),
        verification=verification,
        rollback=rollback,
    )


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be an object")
    return value


def number(value: Any, label: str, *, positive: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if positive and result <= 0:
        raise ValueError(f"{label} must be positive")
    if not positive and result < 0:
        raise ValueError(f"{label} must be non-negative")
    return result


# [Implementation 2] Input validation and resource budget derivation
def load_metrics(path: Path) -> list[dict[str, float | int | date]]:
    required = {
        "date",
        "host_memory_mb",
        "memory_used_mb",
        "disk_total_gb",
        "disk_used_gb",
        "backup_staging_peak_gb",
        "app_oom_restarts",
        "db_pool_max",
        "db_max_connections",
        "db_admin_reserve",
        "p95_ms",
        "error_rate",
    }
    try:
        handle = path.open("r", encoding="utf-8", newline="")
    except OSError as exc:
        raise ValueError(f"cannot read metrics: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or set(reader.fieldnames) != required:
            raise ValueError("metrics CSV columns do not match the required schema")
        rows: list[dict[str, float | int | date]] = []
        for line_number, raw in enumerate(reader, start=2):
            try:
                observed = date.fromisoformat(raw["date"])
                row: dict[str, float | int | date] = {
                    "date": observed,
                    "host_memory_mb": number(float(raw["host_memory_mb"]), "host_memory_mb", positive=True),
                    "memory_used_mb": number(float(raw["memory_used_mb"]), "memory_used_mb"),
                    "disk_total_gb": number(float(raw["disk_total_gb"]), "disk_total_gb", positive=True),
                    "disk_used_gb": number(float(raw["disk_used_gb"]), "disk_used_gb"),
                    "backup_staging_peak_gb": number(float(raw["backup_staging_peak_gb"]), "backup_staging_peak_gb"),
                    "app_oom_restarts": int(raw["app_oom_restarts"]),
                    "db_pool_max": int(raw["db_pool_max"]),
                    "db_max_connections": int(raw["db_max_connections"]),
                    "db_admin_reserve": int(raw["db_admin_reserve"]),
                    "p95_ms": number(float(raw["p95_ms"]), "p95_ms"),
                    "error_rate": number(float(raw["error_rate"]), "error_rate"),
                }
            except (ValueError, KeyError) as exc:
                raise ValueError(f"invalid metrics row {line_number}: {exc}") from exc
            if row["memory_used_mb"] > row["host_memory_mb"]:
                raise ValueError(f"memory usage exceeds host capacity at row {line_number}")
            if row["disk_used_gb"] > row["disk_total_gb"]:
                raise ValueError(f"disk usage exceeds total capacity at row {line_number}")
            if row["app_oom_restarts"] < 0 or row["db_pool_max"] < 0 or row["db_admin_reserve"] < 0:
                raise ValueError(f"negative integer metric at row {line_number}")
            rows.append(row)
    if len(rows) < 2:
        raise ValueError("at least two metrics rows are required")
    dates = [row["date"] for row in rows]
    if dates != sorted(dates) or len(set(dates)) != len(dates):
        raise ValueError("metrics dates must be strictly increasing")
    return rows


def derive(rows: list[dict[str, float | int | date]], policy: dict[str, Any]) -> dict[str, float]:
    first, latest = rows[0], rows[-1]
    span_days = (latest["date"] - first["date"]).days
    if span_days <= 0:
        raise ValueError("metrics window must span at least one day")
    memory_headrooms = [
        (float(row["host_memory_mb"]) - float(row["memory_used_mb"])) / float(row["host_memory_mb"]) * 100
        for row in rows
    ]
    disk_growth_per_day = (float(latest["disk_used_gb"]) - float(first["disk_used_gb"])) / span_days
    disk_alert_percent = number(policy.get("disk_alert_percent"), "disk_alert_percent", positive=True)
    if disk_alert_percent >= 100:
        raise ValueError("disk_alert_percent must be below 100")
    effective_disk_limit = (
        float(latest["disk_total_gb"]) * disk_alert_percent / 100
        - float(latest["backup_staging_peak_gb"])
    )
    if disk_growth_per_day > 0:
        disk_days_remaining = (effective_disk_limit - float(latest["disk_used_gb"])) / disk_growth_per_day
    else:
        disk_days_remaining = math.inf
    database_budget = int(latest["db_max_connections"]) - int(latest["db_admin_reserve"])
    return {
        "latest_memory_headroom_percent": memory_headrooms[-1],
        "minimum_memory_headroom_percent": min(memory_headrooms),
        "disk_growth_gb_per_day": disk_growth_per_day,
        "effective_disk_limit_gb": effective_disk_limit,
        "disk_days_remaining": disk_days_remaining,
        "database_application_budget": float(database_budget),
        "oom_restarts_in_window": float(sum(int(row["app_oom_restarts"]) for row in rows)),
        "latest_p95_ms": float(latest["p95_ms"]),
        "latest_error_rate": float(latest["error_rate"]),
    }


# [Implementation 3] Capacity and SLO findings
def capacity_actions(
    rows: list[dict[str, float | int | date]],
    policy: dict[str, Any],
    derived: dict[str, float],
    as_of: date,
) -> list[Action]:
    latest = rows[-1]
    owners = policy.get("owners")
    if not isinstance(owners, dict):
        raise ValueError("policy.owners must be an object")
    capacity_owner = str(owners.get("capacity", ""))
    database_owner = str(owners.get("database", ""))
    if not capacity_owner or not database_owner:
        raise ValueError("capacity and database owners are required")
    actions: list[Action] = []

    memory_min = number(policy.get("memory_headroom_percent_min"), "memory_headroom_percent_min")
    if derived["latest_memory_headroom_percent"] < memory_min:
        actions.append(
            action(
                "memory-headroom-below-policy",
                "high",
                f"latest={derived['latest_memory_headroom_percent']:.2f}% policy_min={memory_min:.2f}%",
                capacity_owner,
                as_of,
                "Load test at projected peak and confirm headroom remains above policy for 24 hours.",
                "Revert the workload or resource change if latency or OOM behavior regresses.",
            )
        )

    horizon = number(policy.get("disk_horizon_days"), "disk_horizon_days", positive=True)
    disk_days = derived["disk_days_remaining"]
    if disk_days <= 0:
        severity = "critical"
        action_id = "disk-capacity-reserve-exhausted"
    elif disk_days < horizon:
        severity = "high"
        action_id = "disk-capacity-horizon-below-policy"
    else:
        severity = ""
        action_id = ""
    if severity:
        actions.append(
            action(
                action_id,
                severity,
                (
                    f"used={float(latest['disk_used_gb']):.2f}GB "
                    f"effective_limit={derived['effective_disk_limit_gb']:.2f}GB "
                    f"growth={derived['disk_growth_gb_per_day']:.3f}GB/day "
                    f"days_remaining={disk_days:.1f}"
                ),
                capacity_owner,
                as_of,
                "Run backup staging and peak traffic together, then confirm byte and inode alerts remain clear.",
                "Remove newly allocated data or restore the previous volume allocation if the resize path fails.",
            )
        )

    if derived["oom_restarts_in_window"] > 0:
        actions.append(
            action(
                "application-oom-restarts-observed",
                "high",
                f"oom_restarts={int(derived['oom_restarts_in_window'])}",
                capacity_owner,
                as_of,
                "Exercise peak memory paths and observe zero OOM restarts for the full verification window.",
                "Restore the previous memory limit and release if the new configuration increases failures.",
            )
        )

    application_budget = int(derived["database_application_budget"])
    pool_max = int(latest["db_pool_max"])
    if pool_max > application_budget:
        actions.append(
            action(
                "database-connection-reserve-violated",
                "critical",
                f"pool_max={pool_max} application_budget={application_budget}",
                database_owner,
                as_of,
                "Saturate the application pool and confirm administrator connections remain available.",
                "Restore the previous pool size if connection wait time or application errors increase.",
            )
        )

    p95_max = number(policy.get("p95_ms_max"), "p95_ms_max", positive=True)
    if derived["latest_p95_ms"] > p95_max:
        actions.append(
            action(
                "latency-slo-exceeded",
                "high",
                f"latest_p95_ms={derived['latest_p95_ms']:.1f} policy_max={p95_max:.1f}",
                capacity_owner,
                as_of,
                "Verify p95 latency remains below policy under representative peak load.",
                "Roll back the capacity or release change if p95 latency does not recover.",
            )
        )

    error_max = number(policy.get("error_rate_max"), "error_rate_max")
    if derived["latest_error_rate"] > error_max:
        actions.append(
            action(
                "error-rate-slo-exceeded",
                "high",
                f"latest_error_rate={derived['latest_error_rate']:.4f} policy_max={error_max:.4f}",
                capacity_owner,
                as_of,
                "Verify error rate remains below policy during representative traffic and dependency failures.",
                "Return to the previous release or resource policy if the error rate remains elevated.",
            )
        )
    return actions


# [Implementation 4] Component support lifecycle
def component_actions(components: dict[str, Any], policy: dict[str, Any], as_of: date) -> list[Action]:
    if date.fromisoformat(str(components.get("as_of"))) != as_of:
        raise ValueError("components.as_of must match the latest metrics date")
    entries = components.get("components")
    if not isinstance(entries, list):
        raise ValueError("components.components must be an array")
    max_rebuild_age = int(number(policy.get("base_rebuild_max_age_days"), "base_rebuild_max_age_days", positive=True))
    warning_days = int(number(policy.get("support_end_warning_days"), "support_end_warning_days", positive=True))
    actions: list[Action] = []
    names: set[str] = set()
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise ValueError(f"components[{index}] must be an object")
        required = ("name", "current_version", "latest_approved_version", "support_end", "last_rebuilt", "owner")
        if any(not isinstance(raw.get(key), str) or not raw[key].strip() for key in required):
            raise ValueError(f"components[{index}] is missing required strings")
        name = raw["name"]
        if name in names:
            raise ValueError(f"duplicate component: {name}")
        names.add(name)
        support_end = date.fromisoformat(raw["support_end"])
        last_rebuilt = date.fromisoformat(raw["last_rebuilt"])
        support_days = (support_end - as_of).days
        rebuild_age = (as_of - last_rebuilt).days
        version_gap = raw["current_version"] != raw["latest_approved_version"]
        if support_days < 0:
            severity = "critical"
            action_id = f"component-{name}-support-expired"
            reason = f"support expired {-support_days} day(s) ago"
        elif support_days <= warning_days:
            severity = "high"
            action_id = f"component-{name}-support-ending"
            reason = f"support ends in {support_days} day(s)"
        elif rebuild_age > max_rebuild_age or version_gap:
            severity = "medium"
            action_id = f"component-{name}-refresh-required"
            reason = f"rebuild_age={rebuild_age} day(s)"
        else:
            continue
        evidence = (
            f"{reason}; current={raw['current_version']} approved={raw['latest_approved_version']}; "
            f"last_rebuilt={raw['last_rebuilt']} support_end={raw['support_end']}"
        )
        actions.append(
            action(
                action_id,
                severity,
                evidence,
                raw["owner"],
                as_of,
                "Rebuild, scan, deploy through readiness and smoke gates, and observe SLOs for the verification window.",
                "Retain and redeploy the previous exact digest while database and configuration compatibility remain valid.",
            )
        )
    return actions


# [Implementation 5] Deterministic report projection
def analyze(metrics_path: Path, policy_path: Path, components_path: Path) -> dict[str, Any]:
    rows = load_metrics(metrics_path)
    policy = load_json(policy_path, "policy")
    components = load_json(components_path, "components")
    as_of = rows[-1]["date"]
    assert isinstance(as_of, date)
    derived = derive(rows, policy)
    actions = capacity_actions(rows, policy, derived, as_of)
    actions.extend(component_actions(components, policy, as_of))
    actions.sort(key=lambda item: (SEVERITY_ORDER[item.severity], item.id))
    serializable_derived = {
        key: (None if math.isinf(value) else round(value, 6))
        for key, value in sorted(derived.items())
    }
    return {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "window": {
            "start": rows[0]["date"].isoformat(),
            "end": as_of.isoformat(),
            "observations": len(rows),
        },
        "derived": serializable_derived,
        "actions": [asdict(item) for item in actions],
    }


# [Implementation 6] JSON CLI boundary
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a capacity and component update action plan.")
    parser.add_argument("metrics", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument("components", type=Path)
    parser.add_argument("--fail-on-actions", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = analyze(args.metrics, args.policy, args.components)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.fail_on_actions and report["actions"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
