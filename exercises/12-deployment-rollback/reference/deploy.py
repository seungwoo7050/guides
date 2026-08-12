from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DIGEST = re.compile(r"^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$")


# [Implementation 1] current pointer가 crash 뒤에도 보존되도록 durable atomic-write primitive를 먼저 둡니다.
def fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    fsync_directory(path.parent)


# [Implementation 2] 모든 성공·실패 전이를 append-only evidence로 남깁니다.
def append_event(state_dir: Path, event: str, release: str, detail: str = "") -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "release": release,
        "detail": detail,
    }
    payload = (json.dumps(record, sort_keys=True) + "\n").encode()
    event_path = state_dir / "events.jsonl"
    descriptor = os.open(event_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fail(state_dir: Path, release: str, phase: str, detail: str) -> dict[str, Any]:
    append_event(state_dir, "deployment-failed", release, f"{phase}:{detail}")
    return {"status": "failed", "phase": phase, "detail": detail}


# [Implementation 3] 환경 lock을 획득한 process만 preflight와 상태 전이를 소유합니다.
def deploy(state_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    state_dir.mkdir(parents=True, exist_ok=True)
    release = str(manifest.get("release_id", "unknown"))
    lock_path = state_dir / "deployment.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return {"status": "failed", "phase": "lock", "detail": "deployment already in progress"}
    os.write(descriptor, f"pid={os.getpid()}\n".encode())
    os.close(descriptor)

    staged_path = state_dir / "staged.json"
    try:
        current_path = state_dir / "current.json"
        if not current_path.is_file():
            return fail(state_dir, release, "preflight", "current state missing")
        current = json.loads(current_path.read_text(encoding="utf-8"))
        image = manifest.get("image")
        if manifest.get("schema_version") != 1:
            return fail(state_dir, release, "preflight", "unsupported manifest schema")
        if not isinstance(image, str) or not DIGEST.fullmatch(image):
            return fail(state_dir, release, "preflight", "image is not an exact digest")
        if manifest.get("available") is not True:
            return fail(state_dir, release, "preflight", "image unavailable")

        db_schema = current.get("db_schema")
        schema_min = manifest.get("schema_min")
        schema_max = manifest.get("schema_max")
        migration_target = manifest.get("migration_target")
        if not all(isinstance(value, int) for value in (db_schema, schema_min, schema_max, migration_target)):
            return fail(state_dir, release, "preflight", "schema metadata invalid")
        if not schema_min <= db_schema <= schema_max:
            return fail(state_dir, release, "preflight", "current schema is incompatible with candidate")
        if not schema_min <= migration_target <= schema_max:
            return fail(state_dir, release, "preflight", "migration target is outside candidate range")
        previous_compat = current.get("current_compat", {})
        prev_min = previous_compat.get("schema_min")
        prev_max = previous_compat.get("schema_max")
        if not isinstance(prev_min, int) or not isinstance(prev_max, int) or not prev_min <= migration_target <= prev_max:
            return fail(state_dir, release, "preflight", "migration would make automatic rollback incompatible")

        # [Implementation 4] 호환성 preflight 뒤에만 candidate를 stage하고 migration state를 분리합니다.
        append_event(state_dir, "preflight-passed", release)
        atomic_json(staged_path, {"release": release, "image": image, "phase": "starting"})
        append_event(state_dir, "candidate-staged", release)

        # Migration은 candidate release 확정과 별개로 데이터베이스 상태를 바꿉니다.
        # 실패 뒤에도 이전 release가 이 schema를 사용할 수 있음을 preflight에서 확인했습니다.
        migrated_state = dict(current)
        migrated_state["db_schema"] = migration_target
        atomic_json(current_path, migrated_state)
        current = migrated_state
        append_event(state_dir, "migration-applied", release, f"schema={migration_target}")

        # [Implementation 5] readiness와 external smoke는 current 공개 전의 독립 실패 gate입니다.
        if manifest.get("readiness") is not True:
            staged_path.unlink(missing_ok=True)
            append_event(state_dir, "rollback-completed", release, "readiness failed; previous release retained")
            return fail(state_dir, release, "readiness", "candidate not ready")
        append_event(state_dir, "readiness-passed", release)

        if manifest.get("smoke") is not True:
            staged_path.unlink(missing_ok=True)
            append_event(state_dir, "rollback-completed", release, "smoke failed; previous release retained")
            return fail(state_dir, release, "smoke", "external smoke failed")
        append_event(state_dir, "smoke-passed", release)

        # [Implementation 6] 모든 gate 뒤 current·previous·compatibility를 한 번에 원자 교체합니다.
        new_state = {
            "current": release,
            "previous": current.get("current"),
            "db_schema": migration_target,
            "current_compat": {"schema_min": schema_min, "schema_max": schema_max},
            "image": image,
        }
        atomic_json(current_path, new_state)
        staged_path.unlink(missing_ok=True)
        append_event(state_dir, "release-committed", release)
        return {"status": "success", "phase": "committed", "current": release}
    finally:
        lock_path.unlink(missing_ok=True)
