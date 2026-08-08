#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "base-image-stale",
    "db-pool-overcommit",
    "disk-exhaustion-within-horizon",
    "disk-staging-overflow",
    "error-rate-slo-breached",
    "latency-slo-breached",
    "memory-headroom-low",
    "oom-restarts-observed",
    "support-ending-soon:docker-engine",
    "unsupported-component:database",
}


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("capacity_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "reference"}:
        print("사용법: verify.py [skeleton|reference]", file=sys.stderr)
        return 2
    module = load_module(ROOT / sys.argv[1] / "plan.py")
    result = module.analyze(ROOT / "fixtures" / "metrics.csv", ROOT / "fixtures" / "components.json", ROOT / "fixtures" / "policy.json")
    errors: list[str] = []
    if result.get("as_of") != "2026-08-07":
        errors.append("as_of가 fixture 기준과 다릅니다.")
    capacity = result.get("capacity", {})
    headroom = capacity.get("memory_headroom_percent")
    if not isinstance(headroom, (int, float)) or not 14 <= float(headroom) <= 15:
        errors.append(f"memory headroom 계산이 올바르지 않습니다: {headroom}")
    horizon = capacity.get("days_to_disk_threshold")
    if not isinstance(horizon, (int, float)) or not 9 <= float(horizon) <= 11:
        errors.append(f"disk 고갈 horizon 계산이 올바르지 않습니다: {horizon}")
    if capacity.get("db_safe_connection_budget") != 85:
        errors.append("DB safe connection budget은 85여야 합니다.")
    if capacity.get("oom_restarts") != 2:
        errors.append("OOM restart 합계는 2여야 합니다.")
    if capacity.get("p95_ms") != 500.0:
        errors.append("최신 p95는 500ms여야 합니다.")
    if capacity.get("error_rate") != 0.012:
        errors.append("최신 error rate는 0.012여야 합니다.")

    findings = result.get("findings")
    if not isinstance(findings, list):
        errors.append("findings는 목록이어야 합니다.")
        findings = []
    ids = {item.get("id") for item in findings if isinstance(item, dict)}
    missing = EXPECTED - ids
    unexpected = ids - EXPECTED
    if missing:
        errors.append(f"누락 finding: {', '.join(sorted(missing))}")
    if unexpected:
        errors.append(f"예상하지 않은 finding: {', '.join(sorted(str(item) for item in unexpected))}")
    for item in findings:
        if not isinstance(item, dict):
            errors.append(f"finding이 매핑이 아닙니다: {item}")
            continue
        for key in ("id", "severity", "evidence", "action", "owner", "deadline", "verification", "rollback"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"finding {item.get('id')}.{key}가 비어 있습니다.")
        try:
            deadline = date.fromisoformat(item.get("deadline", ""))
            if deadline < date(2026, 8, 7):
                errors.append(f"finding deadline이 과거입니다: {item}")
        except ValueError:
            errors.append(f"finding deadline 형식이 잘못됐습니다: {item}")
    severity = {item.get("id"): item.get("severity") for item in findings if isinstance(item, dict)}
    for critical in ("disk-staging-overflow", "unsupported-component:database"):
        if severity.get(critical) != "critical":
            errors.append(f"{critical}은 critical이어야 합니다.")

    if errors:
        print(f"용량·업데이트 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: headroom, latency/error budget, growth horizon, connection budget, OOM과 update lifecycle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
