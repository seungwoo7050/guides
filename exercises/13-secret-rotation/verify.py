#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import stat
import sys
import tempfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("secret_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "reference"}:
        print("사용법: verify.py [skeleton|reference]", file=sys.stderr)
        return 2
    module = load_module(ROOT / sys.argv[1] / "rotate.py")
    errors: list[str] = []
    first = "correct-horse-battery-v1"
    rejected = "must-not-become-current-v2"
    second = "correct-horse-battery-v2"

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "secrets"
        store = module.SecretStore(root)
        if not store.install("db_password", "v1", first, lambda path: path.read_text(encoding="utf-8") == first):
            errors.append("초기 v1 설치가 실패했습니다.")
        try:
            current = store.current("db_password")
        except Exception as exc:
            errors.append(f"current 조회가 실패했습니다: {exc}")
            current = {}
        if current.get("version") != "v1":
            errors.append("v1이 current가 아닙니다.")

        accepted = store.install("db_password", "v2", rejected, lambda path: False)
        if accepted:
            errors.append("검증 실패한 v2를 성공으로 반환했습니다.")
        if store.current("db_password").get("version") != "v1":
            errors.append("검증 실패한 v2가 current pointer를 바꿨습니다.")
        rejected_path = root / "db_password" / "versions" / "v2"
        if rejected_path.exists():
            errors.append("거부된 v2 후보 파일이 남았습니다.")

        accepted = store.install("db_password", "v2", second, lambda path: path.read_text(encoding="utf-8") == second)
        if not accepted or store.current("db_password").get("version") != "v2":
            errors.append("검증된 v2로 전환하지 못했습니다.")

        def raising_validator(path: Path) -> bool:
            del path
            raise RuntimeError("simulated consumer failure")

        try:
            accepted = store.install(
                "db_password",
                "v3",
                "must-not-survive-v3",
                raising_validator,
            )
        except Exception as exc:
            errors.append(f"validator 예외를 안전한 거부로 처리하지 못했습니다: {exc}")
            accepted = False
        try:
            current_after_exception = store.current("db_password").get("version")
        except Exception as exc:
            errors.append(f"validator 예외 뒤 current 조회가 실패했습니다: {exc}")
            current_after_exception = None
        if accepted or current_after_exception != "v2":
            errors.append("validator 예외가 current pointer를 바꿨습니다.")
        if (root / "db_password" / "versions" / "v3").exists():
            errors.append("validator 예외 뒤 v3 후보 파일이 남았습니다.")

        for unsafe_name, unsafe_version in (("../escape", "v4"), ("db_password", "../v4")):
            try:
                store.install(unsafe_name, unsafe_version, "unsafe-value", lambda path: True)
                errors.append(
                    f"경로를 벗어날 수 있는 secret 이름 또는 version을 허용했습니다: "
                    f"{unsafe_name}/{unsafe_version}"
                )
            except (ValueError, FileExistsError):
                pass
            except Exception as exc:
                errors.append(
                    f"잘못된 이름·version에서 예상하지 않은 예외입니다: "
                    f"{unsafe_name}/{unsafe_version}: {exc}"
                )
        v1 = root / "db_password" / "versions" / "v1"
        v2 = root / "db_password" / "versions" / "v2"
        if not v1.exists() or not v2.exists():
            errors.append("전환 직후 이전·현재 version이 함께 존재해야 합니다.")
        for path in (root, root / "db_password", root / "db_password" / "versions"):
            if path.exists() and mode(path) != 0o700:
                errors.append(f"secret 디렉터리 mode가 700이 아닙니다: {path}={oct(mode(path))}")
        for path in (
            v1,
            v2,
            root / "db_password" / "current.json",
            root / "db_password" / ".rotation.lock",
            root / "audit_hmac_key.bin",
        ):
            if path.exists() and mode(path) != 0o600:
                errors.append(f"secret 파일 mode가 600이 아닙니다: {path}={oct(mode(path))}")

        try:
            store.retire("db_password", "v2")
            errors.append("current v2 retire를 허용했습니다.")
        except (ValueError, RuntimeError):
            pass
        except Exception as exc:
            errors.append(f"current retire가 예상하지 않은 예외를 냈습니다: {exc}")
        store.retire("db_password", "v1")
        if v1.exists():
            errors.append("이전 v1을 retire하지 못했습니다.")

        event_path = root / "events.jsonl"
        if not event_path.is_file():
            errors.append("events.jsonl이 없습니다.")
            event_text = ""
            event_records = []
        else:
            event_text = event_path.read_text(encoding="utf-8")
            event_records = [json.loads(line) for line in event_text.splitlines() if line]
        for secret in (first, rejected, second, "must-not-survive-v3"):
            if secret in event_text:
                errors.append("event log에 secret 원문이 노출되었습니다.")
        if event_path.exists() and mode(event_path) != 0o600:
            errors.append(f"event log mode가 600이 아닙니다: {oct(mode(event_path))}")
        names = [record.get("event") for record in event_records]
        for required in ("candidate-created", "candidate-rejected", "current-switched", "version-retired"):
            if required not in names:
                errors.append(f"secret 수명 주기 event가 없습니다: {required}")
        for record in event_records:
            fingerprint = record.get("fingerprint")
            if not isinstance(fingerprint, str) or not fingerprint.startswith("hmac-sha256:"):
                errors.append(f"keyed fingerprint가 없습니다: {record}")
        direct_hashes = {
            "sha256:" + hashlib.sha256(secret.encode()).hexdigest()[:16]
            for secret in (first, rejected, second, "must-not-survive-v3")
        }
        if any(record.get("fingerprint") in direct_hashes for record in event_records):
            errors.append("낮은 entropy secret을 직접 SHA-256 fingerprint로 노출했습니다.")

    if errors:
        print(f"secret 회전 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: 안전한 권한, 후보 검증, 원자 전환, 폐기와 redacted event")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
