#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "backup-local-only",
    "disk-alert-missing",
    "docker-socket-mounted",
    "ipv6-firewall-unreviewed",
    "non-admin-docker-group",
    "shared-admin-key",
    "ssh-password-authentication",
    "ssh-root-login",
    "time-not-synchronized",
    "unexpected-public-service-port",
    "unprotected-docker-tcp",
    "unrestricted-ssh-source",
}
SEVERITIES = {"low", "medium", "high", "critical"}


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("audit_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"모듈을 불러올 수 없습니다: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "workspace", "reference"}:
        print("사용법: verify.py [skeleton|workspace|reference]", file=sys.stderr)
        return 2
    module = load_module(ROOT / sys.argv[1] / "audit.py")
    if not hasattr(module, "audit"):
        print("audit(snapshot) 함수가 없습니다.", file=sys.stderr)
        return 1

    secure = module.audit(load_json(ROOT / "fixtures" / "secure.json"))
    insecure = module.audit(load_json(ROOT / "fixtures" / "insecure.json"))
    errors: list[str] = []

    if secure:
        errors.append(f"secure snapshot에 false positive가 있습니다: {secure}")
    if not isinstance(insecure, list):
        errors.append("audit 반환값은 목록이어야 합니다.")
        insecure = []

    ids: list[str] = []
    for index, item in enumerate(insecure):
        if not isinstance(item, dict):
            errors.append(f"finding {index}는 매핑이어야 합니다.")
            continue
        for key in ("id", "severity", "evidence", "remediation", "safe_order"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"finding {index}.{key}가 비어 있습니다.")
        if item.get("severity") not in SEVERITIES:
            errors.append(f"finding {index}.severity가 올바르지 않습니다.")
        if isinstance(item.get("id"), str):
            ids.append(item["id"])

    actual = set(ids)
    missing = EXPECTED - actual
    unexpected = actual - EXPECTED
    if missing:
        errors.append(f"찾지 못한 finding: {', '.join(sorted(missing))}")
    if unexpected:
        errors.append(f"증거 없이 추가한 finding: {', '.join(sorted(unexpected))}")
    if len(ids) != len(set(ids)):
        errors.append("finding id가 중복되었습니다.")

    critical_expected = {
        "unprotected-docker-tcp",
        "docker-socket-mounted",
        "non-admin-docker-group",
        "backup-local-only",
    }
    severity_by_id = {item.get("id"): item.get("severity") for item in insecure if isinstance(item, dict)}
    for finding_id in critical_expected:
        if severity_by_id.get(finding_id) != "critical":
            errors.append(f"{finding_id}는 critical로 분류해야 합니다.")

    if errors:
        print(f"호스트 감사 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"통과: {len(insecure)}개 위험과 secure false positive 0건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
