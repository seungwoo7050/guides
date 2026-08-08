#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


def mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label}는 매핑이어야 합니다.")
        return {}
    return value


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().upper() != "TODO"


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"YAML을 읽을 수 없습니다: {exc}"]

    root = mapping(data, "최상위 문서", errors)
    if root.get("schema_version") != 1:
        errors.append("schema_version은 1이어야 합니다.")

    service = mapping(root.get("service"), "service", errors)
    for key in ("name", "user_capability", "owner"):
        if not nonempty(service.get(key)):
            errors.append(f"service.{key}가 비어 있거나 TODO입니다.")
    capability = str(service.get("user_capability", ""))
    if any(word in capability.lower() for word in ("docker", "nginx", "mariadb")):
        errors.append("service.user_capability는 기술 목록보다 사용자 기능으로 작성해야 합니다.")

    endpoints = mapping(root.get("endpoints"), "endpoints", errors)
    public = endpoints.get("public")
    management = endpoints.get("management")
    if not isinstance(public, list) or not public:
        errors.append("endpoints.public에 공개 endpoint가 필요합니다.")
        public = []
    if not isinstance(management, list) or not management:
        errors.append("endpoints.management에 관리 endpoint가 필요합니다.")
        management = []

    public_ports: set[int] = set()
    for index, item in enumerate(public):
        endpoint = mapping(item, f"endpoints.public[{index}]", errors)
        port = endpoint.get("port")
        if isinstance(port, int):
            public_ports.add(port)
            if port not in {80, 443}:
                errors.append(f"공개 기준선에서 의도하지 않은 port입니다: {port}")
        else:
            errors.append(f"endpoints.public[{index}].port는 정수여야 합니다.")
        for key in ("name", "protocol", "owner"):
            if not nonempty(endpoint.get(key)):
                errors.append(f"endpoints.public[{index}].{key}가 필요합니다.")
    if 443 not in public_ports:
        errors.append("공개 HTTPS 443 endpoint가 필요합니다.")

    for index, item in enumerate(management):
        endpoint = mapping(item, f"endpoints.management[{index}]", errors)
        for key in ("name", "protocol", "source_restriction", "owner"):
            if not nonempty(endpoint.get(key)):
                errors.append(f"endpoints.management[{index}].{key}가 필요합니다.")
        restriction = str(endpoint.get("source_restriction", "")).lower()
        if restriction in {"any", "0.0.0.0/0", "::/0", "public"}:
            errors.append("관리 endpoint의 출발지 제한이 너무 넓습니다.")

    data_items = root.get("data")
    if not isinstance(data_items, list) or len(data_items) < 3:
        errors.append("업무 데이터·secret·configuration을 포함한 data 목록이 필요합니다.")
        data_items = []
    classifications: set[str] = set()
    for index, item in enumerate(data_items):
        entry = mapping(item, f"data[{index}]", errors)
        classification = entry.get("classification")
        if isinstance(classification, str):
            classifications.add(classification)
        for key in ("name", "classification", "source_of_truth", "recovery_source", "owner"):
            if not nonempty(entry.get(key)):
                errors.append(f"data[{index}].{key}가 필요합니다.")
        if entry.get("external_recovery_copy") is not True:
            errors.append(f"data[{index}]는 host 밖의 복구 원본을 명시해야 합니다.")
        rpo = entry.get("rpo_minutes")
        if not isinstance(rpo, int) or rpo < 0:
            errors.append(f"data[{index}].rpo_minutes는 0 이상의 정수여야 합니다.")
    if not {"business", "secret", "configuration"}.issubset(classifications):
        errors.append("data classification에 business, secret, configuration이 모두 필요합니다.")

    objectives = mapping(root.get("objectives"), "objectives", errors)
    for key in ("rto_minutes", "rpo_minutes"):
        value = objectives.get(key)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"objectives.{key}는 양의 정수여야 합니다.")
    availability = mapping(objectives.get("availability"), "objectives.availability", errors)
    if not nonempty(availability.get("path")) or availability.get("path") == "/healthz":
        errors.append("가용성 측정은 고정 healthz보다 실제 사용자 경로를 사용해야 합니다.")
    if str(availability.get("measurement_location", "")).lower() in {"host", "localhost", "container"}:
        errors.append("가용성 측정 위치는 host 밖의 external probe여야 합니다.")
    target = availability.get("target_percent")
    if not isinstance(target, (int, float)) or not 90 <= float(target) <= 100:
        errors.append("availability.target_percent는 90~100 범위여야 합니다.")
    window = availability.get("window_days")
    if not isinstance(window, int) or window <= 0:
        errors.append("availability.window_days는 양의 정수여야 합니다.")

    threat = mapping(root.get("threat_model"), "threat_model", errors)
    boundaries = threat.get("trust_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) < 4 or not all(nonempty(v) for v in boundaries):
        errors.append("trust boundary를 네 개 이상 명시해야 합니다.")
    risks = threat.get("risks")
    if not isinstance(risks, list) or len(risks) < 4:
        errors.append("대표 risk를 네 개 이상 명시해야 합니다.")
        risks = []
    ids: set[str] = set()
    for index, item in enumerate(risks):
        risk = mapping(item, f"threat_model.risks[{index}]", errors)
        for key in ("id", "scenario", "prevention", "detection", "recovery", "owner"):
            if not nonempty(risk.get(key)):
                errors.append(f"threat_model.risks[{index}].{key}가 필요합니다.")
        risk_id = risk.get("id")
        if isinstance(risk_id, str):
            if risk_id in ids:
                errors.append(f"중복 risk id입니다: {risk_id}")
            ids.add(risk_id)

    residual = root.get("residual_risks")
    if not isinstance(residual, list) or not residual:
        errors.append("단일 host 잔여 위험을 명시해야 합니다.")
        residual = []
    if not any("single-host" in str(item.get("id", "")) for item in residual if isinstance(item, dict)):
        errors.append("single-host-outage 잔여 위험이 필요합니다.")
    for index, item in enumerate(residual):
        risk = mapping(item, f"residual_risks[{index}]", errors)
        for key in ("id", "statement", "accepted_by", "mitigation"):
            if not nonempty(risk.get(key)):
                errors.append(f"residual_risks[{index}].{key}가 필요합니다.")

    readiness = mapping(root.get("readiness"), "readiness", errors)
    for key in (
        "immutable_release",
        "external_backup",
        "rollback_tested",
        "certificate_monitored",
        "restore_drill_tested",
    ):
        if readiness.get(key) is not True:
            errors.append(f"readiness.{key}가 true여야 합니다.")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("사용법: verify.py PATH", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        print(f"운영 계약 검사 실패: {len(errors)}건", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        return 1
    print(f"통과: 운영 계약 {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
