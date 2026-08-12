#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DIGEST = re.compile(r"^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
REVISION = re.compile(r"^[0-9a-f]{12,64}$")
EXPECTED_STAGES = [
    "declare", "host", "release", "secrets", "restore", "internal-smoke",
    "tls", "dns", "external-smoke", "observability", "finalize",
]
EXPECTED_DRILLS = {
    "wrong-image-digest", "missing-secret", "corrupt-backup",
    "hostname-mismatch", "disk-pressure", "bad-release-rollback",
}


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.strip().upper() != "TODO"


def mapping(value: Any, label: str, errors: list[str]) -> dict:
    if not isinstance(value, dict):
        errors.append(f"{label}는 매핑이어야 합니다.")
        return {}
    return value


def parse_time(value: Any, label: str, errors: list[str]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} 시각 형식이 잘못됐습니다: {value}")
        return None
    if parsed.utcoffset() is None:
        errors.append(f"{label}에는 UTC offset이 필요합니다: {value}")
        return None
    return parsed


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "workspace", "reference"}:
        print("사용법: verify.py [skeleton|workspace|reference]", file=sys.stderr)
        return 2
    path = ROOT / sys.argv[1] / "rebuild-plan.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    root = mapping(data, "plan", errors)
    if root.get("schema_version") != 1 or not nonempty(root.get("exercise_id")):
        errors.append("schema_version 1과 exercise_id가 필요합니다.")

    objectives = mapping(root.get("objectives"), "objectives", errors)
    for key in ("rto_minutes", "rpo_minutes"):
        if not isinstance(objectives.get(key), int) or objectives[key] <= 0:
            errors.append(f"objectives.{key}는 양의 정수여야 합니다.")

    inputs = mapping(root.get("inputs"), "inputs", errors)
    release = mapping(inputs.get("release"), "inputs.release", errors)
    for key in ("release_id", "source_revision"):
        if not nonempty(release.get(key)):
            errors.append(f"inputs.release.{key}가 필요합니다.")
    if not isinstance(release.get("source_revision"), str) or not REVISION.fullmatch(release["source_revision"]):
        errors.append("inputs.release.source_revision은 12자 이상의 hex revision이어야 합니다.")
    config_schema = release.get("configuration_schema")
    rel_min, rel_max = release.get("database_schema_min"), release.get("database_schema_max")
    if not isinstance(config_schema, int) or config_schema <= 0:
        errors.append("release configuration_schema는 양의 정수여야 합니다.")
    if not isinstance(rel_min, int) or not isinstance(rel_max, int) or rel_min > rel_max:
        errors.append("release database schema 호환 범위가 올바르지 않습니다.")
    images = mapping(release.get("images"), "inputs.release.images", errors)
    if not {"gateway", "app", "database"}.issubset(images):
        errors.append("gateway·app·database image가 필요합니다.")
    for name, image in images.items():
        if not isinstance(image, str) or not DIGEST.fullmatch(image):
            errors.append(f"{name} image는 exact digest여야 합니다.")
    if release.get("provenance_verified") is not True:
        errors.append("release provenance 검증이 필요합니다.")

    rollback = mapping(inputs.get("rollback"), "inputs.rollback", errors)
    if not nonempty(rollback.get("release_id")) or not isinstance(rollback.get("app_image"), str) or not DIGEST.fullmatch(rollback["app_image"]):
        errors.append("호환되는 exact rollback release와 digest가 필요합니다.")
    rb_min, rb_max = rollback.get("database_schema_min"), rollback.get("database_schema_max")
    if not isinstance(rb_min, int) or not isinstance(rb_max, int) or rb_min > rb_max:
        errors.append("rollback schema 호환 범위가 올바르지 않습니다.")
    elif isinstance(rel_min, int) and isinstance(rel_max, int) and max(rel_min, rb_min) > min(rel_max, rb_max):
        errors.append("선택 release와 rollback release의 schema 호환 범위가 겹치지 않습니다.")

    backup = mapping(inputs.get("backup"), "inputs.backup", errors)
    for key in ("backup_id", "external_location", "latest_record_at"):
        if not nonempty(backup.get(key)):
            errors.append(f"inputs.backup.{key}가 필요합니다.")
    if not isinstance(backup.get("manifest_sha256"), str) or not SHA.fullmatch(backup["manifest_sha256"]):
        errors.append("backup manifest SHA-256이 필요합니다.")
    external_location = str(backup.get("external_location", ""))
    parsed_location = urlsplit(external_location)
    if parsed_location.scheme in {"", "file"} or not parsed_location.netloc:
        errors.append("backup은 host 밖의 명시적인 원격 URI여야 합니다.")
    backup_latest = parse_time(backup.get("latest_record_at"), "inputs.backup.latest_record_at", errors)

    secrets = inputs.get("secrets")
    if not isinstance(secrets, list) or len(secrets) < 3:
        errors.append("runtime, session, backup key의 versioned secret 원본이 필요합니다.")
        secrets = []
    secret_names: set[str] = set()
    for index, item in enumerate(secrets):
        secret = mapping(item, f"inputs.secrets[{index}]", errors)
        for key in ("name", "source", "owner"):
            if not nonempty(secret.get(key)):
                errors.append(f"inputs.secrets[{index}].{key}가 필요합니다.")
        name = secret.get("name")
        if isinstance(name, str):
            if name in secret_names:
                errors.append(f"secret 이름이 중복되었습니다: {name}")
            secret_names.add(name)
        if str(secret.get("source", "")).lower() in {"host", "host-file", "repository", "repo", "image"}:
            errors.append(f"secret 복구 원본이 손실 host나 release에 묶여 있습니다: {name}")
        if any(key in secret for key in ("value", "password", "token", "private_key")):
            errors.append(f"plan에 secret 값 필드를 넣을 수 없습니다: inputs.secrets[{index}]")

    stages = root.get("stages")
    if not isinstance(stages, list):
        errors.append("stages는 목록이어야 합니다.")
        stages = []
    stage_ids = [item.get("id") for item in stages if isinstance(item, dict)]
    if stage_ids != EXPECTED_STAGES:
        errors.append(f"stage 순서가 안전한 기준선과 다릅니다: {stage_ids}")
    orders: list[int] = []
    for index, item in enumerate(stages):
        stage = mapping(item, f"stages[{index}]", errors)
        if isinstance(stage.get("order"), int):
            orders.append(stage["order"])
        else:
            errors.append(f"stages[{index}].order가 정수여야 합니다.")
        if not nonempty(stage.get("owner")):
            errors.append(f"stages[{index}].owner가 필요합니다.")
        for key in ("halt_conditions", "evidence"):
            value = stage.get(key)
            if not isinstance(value, list) or not value or not all(nonempty(item) for item in value):
                errors.append(f"stages[{index}].{key}가 필요합니다.")
    if orders != list(range(1, len(EXPECTED_STAGES) + 1)):
        errors.append("stage order는 1부터 연속이어야 합니다.")

    smoke = mapping(root.get("external_smoke"), "external_smoke", errors)
    command = str(smoke.get("command", ""))
    if not command or "https://" not in command or "--fail" not in command:
        errors.append("external smoke는 HTTPS와 HTTP 오류 실패 처리를 사용해야 합니다.")
    if re.search(r"(^|\s)(-k|--insecure)(\s|$)", command):
        errors.append("external smoke에서 TLS 검증을 끌 수 없습니다.")
    validates = smoke.get("validates")
    required_validations = {
        "public DNS",
        "TLS hostname and chain",
        "gateway",
        "application",
        "database read",
    }
    validation_values = {item for item in validates if isinstance(item, str)} if isinstance(validates, list) else set()
    if not required_validations.issubset(validation_values):
        errors.append("external smoke가 DNS·TLS·gateway·app·DB 경계를 검증해야 합니다.")
    write_probe = mapping(smoke.get("write_probe"), "external_smoke.write_probe", errors)
    for key in ("idempotency_key", "cleanup"):
        if not nonempty(write_probe.get(key)):
            errors.append(f"external_smoke.write_probe.{key}가 필요합니다.")

    observability = mapping(root.get("observability"), "observability", errors)
    for key in ("external_probe", "structured_logs", "metrics", "certificate_expiry_metric", "backup_age_metric", "test_alert_delivered"):
        if observability.get(key) is not True:
            errors.append(f"observability.{key}가 true여야 합니다.")

    measurements = mapping(root.get("measurements"), "measurements", errors)
    declared = parse_time(measurements.get("recovery_declared_at"), "recovery_declared_at", errors)
    recovered = parse_time(measurements.get("service_recovered_at"), "service_recovered_at", errors)
    source_write = parse_time(measurements.get("latest_source_write_at"), "latest_source_write_at", errors)
    restored_write = parse_time(measurements.get("latest_restored_write_at"), "latest_restored_write_at", errors)
    if declared and recovered:
        rto = (recovered - declared).total_seconds() / 60
        if rto < 0 or rto > objectives.get("rto_minutes", 0):
            errors.append(f"실제 RTO {rto:.1f}분이 목표를 초과하거나 음수입니다.")
    if source_write and restored_write:
        rpo = (source_write - restored_write).total_seconds() / 60
        if rpo < 0 or rpo > objectives.get("rpo_minutes", 0):
            errors.append(f"실제 RPO {rpo:.1f}분이 목표를 초과하거나 음수입니다.")
    if backup_latest and restored_write and backup_latest != restored_write:
        errors.append("backup manifest의 latest_record_at과 실제 restored write 시각이 다릅니다.")

    drills = root.get("failure_drills")
    if not isinstance(drills, list):
        errors.append("failure_drills가 필요합니다.")
        drills = []
    drill_ids = {item.get("id") for item in drills if isinstance(item, dict)}
    missing = EXPECTED_DRILLS - drill_ids
    if missing:
        errors.append(f"failure drill 누락: {', '.join(sorted(missing))}")
    for index, item in enumerate(drills):
        drill = mapping(item, f"failure_drills[{index}]", errors)
        if not nonempty(drill.get("expected_gate")):
            errors.append(f"failure_drills[{index}].expected_gate가 필요합니다.")

    followups = root.get("followups")
    if not isinstance(followups, list) or not followups:
        errors.append("실제 훈련에서 발견한 followup이 필요합니다.")
        followups = []
    for index, item in enumerate(followups):
        followup = mapping(item, f"followups[{index}]", errors)
        for key in ("id", "owner", "deadline", "verification"):
            if not nonempty(followup.get(key)):
                errors.append(f"followups[{index}].{key}가 필요합니다.")
        try:
            deadline = date.fromisoformat(str(followup.get("deadline")))
            if deadline < date(2026, 8, 7):
                errors.append(f"followups[{index}].deadline이 훈련일보다 이전입니다.")
        except ValueError:
            errors.append(f"followups[{index}].deadline 형식이 잘못됐습니다.")

    raw = path.read_text(encoding="utf-8").lower()
    for forbidden in ("password:", "token:", "private_key:", "secret_value", "curl -k", "--insecure"):
        if forbidden in raw:
            errors.append(f"plan에 금지된 secret 또는 TLS 우회가 있습니다: {forbidden}")

    if errors:
        print(f"production rebuild 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: exact release, external backup, safe stages, TLS, RPO/RTO, alerts와 failure drills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
