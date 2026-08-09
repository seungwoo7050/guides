#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

CODE = "GUIDE_SEMANTIC:backfill-plan"


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise AssertionError("interval timestamps must be timezone-aware")
    return parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    try:
        target = Path(sys.argv[1]).resolve()
        plan = json.loads((target / "plan.json").read_text(encoding="utf-8"))
        for field in ("backfill_id", "reason", "owner", "input_snapshots", "transform_revision", "schema_versions", "reference_versions"):
            require(bool(plan.get(field)), f"missing {field}")
        interval = plan.get("interval", {})
        start = parse_time(str(interval.get("start", "")))
        end = parse_time(str(interval.get("end", "")))
        require(start < end, "interval start must be before end")
        require(interval.get("semantics") == "[start,end)", "interval semantics must be explicit")
        require(all(bool(v) for v in plan["input_snapshots"].values()), "all source snapshots must be pinned")
        isolation = plan.get("isolation", {})
        require(isolation.get("mode") in {"separate-output", "versioned-partitions"}, "backfill output must be isolated")
        require(isolation.get("live_writer_conflict") == "forbidden", "live/backfill conflict policy missing")
        canary = plan.get("canary", {})
        require(canary.get("approval_required") is True, "canary approval must be required")
        require(len(plan.get("stop_conditions", [])) >= 2, "at least two stop conditions required")
        reconciliation = plan.get("reconciliation", {})
        require(bool(reconciliation.get("count")), "count reconciliation missing")
        require(bool(reconciliation.get("keys")), "key reconciliation missing")
        require(len(reconciliation.get("aggregates", [])) >= 1, "aggregate reconciliation missing")
        publish = plan.get("publish", {})
        require(publish.get("mode") in {"staged-snapshot-swap", "versioned-promotion"}, "publish must be staged")
        require(publish.get("requires_canary_approval") is True, "publish must require canary approval")
        require(bool(plan.get("resume", {}).get("checkpoint_key")), "resume checkpoint missing")
        require(plan.get("resume", {}).get("completed_intervals_are_immutable") is True, "completed interval contract missing")
        require(bool(plan.get("rollback", {}).get("method")), "rollback method missing")
        require(plan.get("rollback", {}).get("previous_snapshot_recorded") is True, "previous snapshot must be recorded")
        require(isinstance(plan.get("dry_run"), bool), "dry_run flag missing")
    except Exception as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    print("OK backfill-plan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
