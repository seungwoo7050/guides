#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

DIGEST = re.compile(r"^[a-z0-9./_-]+(?::[a-zA-Z0-9._-]+)?@sha256:([0-9a-f]{64})$")
SECRET_NAME = re.compile(r"^[a-z][a-z0-9_]*_v[0-9]+$")


def validate_dockerfile(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    arg_defaults = {
        match.group(1): match.group(2)
        for match in re.finditer(
            r"(?mi)^ARG\s+([A-Za-z_][A-Za-z0-9_]*)=([^\s#]+)",
            text,
        )
    }
    from_matches = list(
        re.finditer(
            r"(?mi)^FROM(?:\s+--platform=[^\s]+)?\s+([^\s]+)",
            text,
        )
    )
    if not from_matches:
        errors.append("Dockerfile에 FROM이 없습니다.")
    for match in from_matches:
        token = match.group(1)
        variable = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", token)
        resolved = arg_defaults.get(variable.group(1), "") if variable else token
        if not resolved:
            errors.append(f"FROM 변수에 명시적인 기본 image가 없습니다: {token}")
            continue
        if resolved != "scratch" and ":" not in resolved.rsplit("/", 1)[-1] and "@sha256:" not in resolved:
            errors.append(f"base image에 명시적인 tag 또는 digest가 없습니다: {resolved}")
        if re.search(r"(?i)(^|:)latest(?:@|$)", resolved):
            errors.append("latest base image를 사용할 수 없습니다.")
    if not re.search(r"(?mi)^USER\s+(?!root\b)\S+", text):
        errors.append("비root USER가 필요합니다.")
    if not re.search(r"(?mi)^(ENTRYPOINT|CMD)\s+\[", text):
        errors.append("exec 형식 ENTRYPOINT 또는 CMD가 필요합니다.")
    labels = {
        "org.opencontainers.image.source",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.version",
        "org.opencontainers.image.created",
    }
    for label in labels:
        if label not in text:
            errors.append(f"OCI label이 없습니다: {label}")
    forbidden = re.compile(r"(?i)(password|secret|token|private[_-]?key)")
    for line_no, line in enumerate(text.splitlines(), 1):
        match = re.match(r"\s*(ARG|ENV)\s+([^=\s]+)", line)
        if match and forbidden.search(match.group(2)):
            errors.append(f"민감한 ARG/ENV 이름을 사용할 수 없습니다: {line_no}:{match.group(2)}")
    return errors


def mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label}는 매핑이어야 합니다.")
        return {}
    return value


def validate_release(path: Path) -> list[str]:
    errors: list[str] = []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = mapping(data, "release", errors)
    if root.get("schema_version") != 1:
        errors.append("schema_version은 1이어야 합니다.")
    for key in ("release_id", "source_revision", "created_at"):
        value = root.get(key)
        if not isinstance(value, str) or not value.strip() or value.strip().upper() == "TODO":
            errors.append(f"{key}가 필요합니다.")
    revision = str(root.get("source_revision", ""))
    if not re.fullmatch(r"[0-9a-f]{12,64}", revision):
        errors.append("source_revision은 12자 이상의 hex revision이어야 합니다.")

    component = mapping(root.get("component"), "component", errors)
    image = str(component.get("image", ""))
    match = DIGEST.fullmatch(image)
    if not match:
        errors.append("component.image는 exact sha256 digest여야 합니다.")
        image_digest = ""
    else:
        image_digest = f"sha256:{match.group(1)}"

    compatibility = mapping(root.get("compatibility"), "compatibility", errors)
    db = mapping(compatibility.get("database_schema"), "compatibility.database_schema", errors)
    db_min, db_max = db.get("min"), db.get("max")
    if not isinstance(db_min, int) or not isinstance(db_max, int) or db_min <= 0 or db_min > db_max:
        errors.append("database schema min/max 범위가 올바르지 않습니다.")
    config_schema = compatibility.get("configuration_schema")
    if not isinstance(config_schema, int) or config_schema <= 0:
        errors.append("configuration_schema는 양의 정수여야 합니다.")

    secrets = mapping(root.get("required_secrets"), "required_secrets", errors)
    if not secrets:
        errors.append("required_secrets가 비어 있습니다.")
    for role, name in secrets.items():
        if not isinstance(role, str) or not isinstance(name, str) or not SECRET_NAME.fullmatch(name):
            errors.append(f"secret은 값이 아니라 versioned 이름이어야 합니다: {role}={name}")

    rollback = mapping(root.get("rollback"), "rollback", errors)
    rollback_image = str(rollback.get("image", ""))
    if not DIGEST.fullmatch(rollback_image):
        errors.append("rollback.image는 exact sha256 digest여야 합니다.")
    if not isinstance(rollback.get("release_id"), str) or not rollback["release_id"].strip():
        errors.append("rollback.release_id가 필요합니다.")
    rollback_db = mapping(rollback.get("database_schema"), "rollback.database_schema", errors)
    rb_min, rb_max = rollback_db.get("min"), rollback_db.get("max")
    if not isinstance(rb_min, int) or not isinstance(rb_max, int) or rb_min <= 0 or rb_min > rb_max:
        errors.append("rollback database schema 범위가 올바르지 않습니다.")
    elif isinstance(db_min, int) and isinstance(db_max, int) and max(db_min, rb_min) > min(db_max, rb_max):
        errors.append("후보와 rollback release의 schema 호환 범위가 겹치지 않습니다.")

    supply = mapping(root.get("supply_chain"), "supply_chain", errors)
    sbom = mapping(supply.get("sbom"), "supply_chain.sbom", errors)
    if sbom.get("generated") is not True or sbom.get("format") not in {"spdx-json", "cyclonedx-json"}:
        errors.append("SBOM 생성과 지원 형식이 필요합니다.")
    if sbom.get("subject_digest") != image_digest:
        errors.append("SBOM subject digest가 배포 image와 다릅니다.")
    provenance = mapping(supply.get("provenance"), "supply_chain.provenance", errors)
    if provenance.get("generated") is not True or provenance.get("verified_before_deploy") is not True:
        errors.append("provenance 생성과 배포 전 검증이 필요합니다.")
    if provenance.get("source_revision") != revision:
        errors.append("provenance source revision이 release와 다릅니다.")

    registry = mapping(root.get("registry"), "registry", errors)
    if registry.get("production_pull_scope") != "read-only":
        errors.append("production registry credential은 read-only여야 합니다.")
    if registry.get("immutable_tags") is not True:
        errors.append("registry immutable tag 정책을 명시해야 합니다.")
    retain = registry.get("retain_rollback_days")
    if not isinstance(retain, int) or retain <= 0:
        errors.append("rollback image 보존 기간이 필요합니다.")

    verification = mapping(root.get("verification"), "verification", errors)
    paths = verification.get("smoke_paths")
    if not isinstance(paths, list) or len(paths) < 2 or not all(isinstance(item, str) and item.startswith("/") for item in paths):
        errors.append("health와 사용자 경로를 포함한 smoke_paths가 필요합니다.")
    return errors


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "workspace", "reference"}:
        print("사용법: verify.py [skeleton|workspace|reference]", file=sys.stderr)
        return 2
    directory = Path(__file__).resolve().parent / sys.argv[1]
    errors = validate_dockerfile(directory / "Dockerfile") + validate_release(directory / "release.yaml")
    if errors:
        print(f"release 산출물 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: Dockerfile, digest, compatibility, SBOM, provenance와 rollback 계약")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
