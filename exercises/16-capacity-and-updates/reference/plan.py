from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any


# [Implementation 1] finding을 evidence·owner·deadline·verify·rollback이 있는 stable action schema로 만듭니다.
def action(finding_id: str, severity: str, evidence: str, action_text: str, owner: str, as_of: date, days: int, verification: str, rollback: str) -> dict[str, Any]:
    return {
        "id": finding_id,
        "severity": severity,
        "evidence": evidence,
        "action": action_text,
        "owner": owner,
        "deadline": (as_of + timedelta(days=days)).isoformat(),
        "verification": verification,
        "rollback": rollback,
    }


# [Implementation 2] input와 time range를 검증한 뒤 derived resource budget을 계산합니다.
def analyze(metrics_path: Path, components_path: Path, policy_path: Path) -> dict:
    with metrics_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    components_data = json.loads(components_path.read_text(encoding="utf-8"))
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if len(rows) < 2:
        raise ValueError("at least two metric rows are required")
    as_of = date.fromisoformat(components_data["as_of"])
    latest = rows[-1]
    first = rows[0]
    elapsed = (date.fromisoformat(latest["date"]) - date.fromisoformat(first["date"])).days
    if elapsed <= 0:
        raise ValueError("metric dates are not increasing")

    total_mem = float(latest["host_memory_mb"])
    used_mem = float(latest["memory_used_mb"])
    memory_headroom = (total_mem - used_mem) / total_mem * 100
    disk_total = float(latest["disk_total_gb"])
    disk_latest = float(latest["disk_used_gb"])
    disk_first = float(first["disk_used_gb"])
    disk_growth = (disk_latest - disk_first) / elapsed
    disk_threshold = disk_total * float(policy["disk_alert_percent"]) / 100
    days_to_threshold = (disk_threshold - disk_latest) / disk_growth if disk_growth > 0 else None
    staging_peak = float(latest["backup_staging_peak_gb"])
    db_pool = int(latest["db_pool_max"])
    db_budget = int(latest["db_max_connections"]) - int(latest["db_admin_reserve"])
    oom_total = sum(int(row["app_oom_restarts"]) for row in rows)
    p95_ms = float(latest["p95_ms"])
    error_rate = float(latest["error_rate"])

    # [Implementation 3] capacity·OOM·latency·error 증거를 실행 가능한 finding으로 바꿉니다.
    owners = policy["owners"]
    findings: list[dict[str, Any]] = []
    if memory_headroom < float(policy["memory_headroom_percent_min"]):
        findings.append(action(
            "memory-headroom-low", "high",
            f"latest headroom={memory_headroom:.1f}%",
            "application·database peak를 분리 측정하고 limit 또는 host memory를 조정한다.",
            owners["capacity"], as_of, 7,
            "대표 부하에서 headroom 20% 이상이며 OOM 0건",
            "이전 resource limit과 host 크기로 되돌리고 latency·OOM을 재확인",
        ))
    if disk_latest + staging_peak >= disk_threshold:
        findings.append(action(
            "disk-staging-overflow", "critical",
            f"used={disk_latest:.1f}GB + staging={staging_peak:.1f}GB >= threshold={disk_threshold:.1f}GB",
            "backup staging을 별도 filesystem 또는 streaming upload로 이동하고 즉시 여유를 확보한다.",
            owners["capacity"], as_of, 2,
            "전체 backup 중 peak disk가 alert threshold 아래",
            "기존 staging 경로를 유지한 채 새 경로 검증 실패 시 전환 취소",
        ))
    if days_to_threshold is not None and days_to_threshold < float(policy["disk_horizon_days"]):
        findings.append(action(
            "disk-exhaustion-within-horizon", "high",
            f"growth={disk_growth:.3f}GB/day, days_to_{policy['disk_alert_percent']}%={days_to_threshold:.1f}",
            "증가 원인을 분류하고 보존 정책 조정 또는 disk 확장을 예약한다.",
            owners["capacity"], as_of, 7,
            "30일 예측 고갈 시점이 정책 horizon 밖이며 byte·inode 경보가 동작",
            "확장 전 snapshot과 filesystem rollback 절차 확인",
        ))
    if db_pool > db_budget:
        findings.append(action(
            "db-pool-overcommit", "high",
            f"pool={db_pool}, safe_budget={db_budget}",
            "app pool 합계를 관리자·migration reserve를 제외한 DB budget 이하로 제한한다.",
            owners["database"], as_of, 3,
            "동시 부하에서 connection 거부 0건과 관리자 연결 여유 유지",
            "이전 pool 설정으로 복귀하고 request concurrency를 임시 제한",
        ))
    if oom_total > 0:
        findings.append(action(
            "oom-restarts-observed", "high",
            f"30-day app OOM restarts={oom_total}",
            "OOM 시각의 release·memory profile을 확인하고 heap·container budget을 수정한다.",
            owners["capacity"], as_of, 3,
            "대표 peak와 배포 겹침 시험에서 OOM 0건",
            "새 limit 또는 runtime 설정을 이전 release 설정으로 복원",
        ))
    if p95_ms > float(policy["p95_ms_max"]):
        findings.append(action(
            "latency-slo-breached", "high",
            f"latest p95={p95_ms:.1f}ms > budget={float(policy['p95_ms_max']):.1f}ms",
            "release·DB wait·CPU·connection queue를 분해하고 대표 부하에서 병목을 재현한다.",
            owners["capacity"], as_of, 3,
            "같은 workload에서 p95가 budget 이하이고 오류율이 악화되지 않음",
            "변경한 concurrency·pool·resource 설정을 이전 값으로 복원",
        ))
    if error_rate > float(policy["error_rate_max"]):
        findings.append(action(
            "error-rate-slo-breached", "high",
            f"latest error_rate={error_rate:.4f} > budget={float(policy['error_rate_max']):.4f}",
            "오류를 status·route·dependency·release로 분류하고 가장 큰 실패 경계를 완화한다.",
            owners["capacity"], as_of, 2,
            "외부 probe와 실제 요청 오류율이 budget 이하로 관찰 창 동안 유지",
            "완화 변경이 오류를 늘리면 이전 exact release와 설정으로 복귀",
        ))

    # [Implementation 4] component support end와 base rebuild lifecycle을 별도로 판정합니다.
    max_age = int(policy["base_rebuild_max_age_days"])
    warning_days = int(policy["support_end_warning_days"])
    for component in components_data.get("components", []):
        name = component["name"]
        support_end = date.fromisoformat(component["support_end"])
        last_rebuilt = date.fromisoformat(component["last_rebuilt"])
        if support_end < as_of:
            findings.append(action(
                f"unsupported-component:{name}", "critical",
                f"support ended {support_end.isoformat()}",
                "지원되는 후보 version으로 image를 빌드하고 복원·부하·rollback 검증 뒤 배포한다.",
                component["owner"], as_of, 2,
                "지원 version의 새 digest, SBOM, staging smoke와 rollback 성공",
                "data format이 호환될 때 이전 exact digest; 비호환이면 사전 복원 지점 사용",
            ))
        elif (support_end - as_of).days <= warning_days:
            findings.append(action(
                f"support-ending-soon:{name}", "medium",
                f"support ends in {(support_end - as_of).days} days",
                "지원 종료 전 업데이트 release와 maintenance window를 계획한다.",
                component["owner"], as_of, 14,
                "후보 version의 compatibility test와 배포 일정 승인",
                "현재 exact digest와 host snapshot 유지",
            ))
        if name == "base-image" and (as_of - last_rebuilt).days > max_age:
            findings.append(action(
                "base-image-stale", "medium",
                f"last rebuilt {(as_of - last_rebuilt).days} days ago",
                "동일 source revision을 최신 승인 base로 재빌드해 scan·SBOM·회귀를 수행한다.",
                component["owner"], as_of, 7,
                "새 base digest의 test·scan·staging 결과 통과",
                "현재 application digest 유지 또는 재배포",
            ))

    # [Implementation 5] 계산값과 ID 정렬 finding을 재현 가능한 report로 투영합니다.
    return {
        "as_of": as_of.isoformat(),
        "capacity": {
            "memory_headroom_percent": round(memory_headroom, 2),
            "disk_growth_gb_per_day": round(disk_growth, 3),
            "days_to_disk_threshold": round(days_to_threshold, 2) if days_to_threshold is not None else None,
            "db_safe_connection_budget": db_budget,
            "oom_restarts": oom_total,
            "p95_ms": round(p95_ms, 2),
            "error_rate": round(error_rate, 6),
        },
        "findings": sorted(findings, key=lambda item: item["id"]),
    }
