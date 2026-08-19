#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

DIGEST = re.compile(r"^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$")


# [Implementation 1] Durable atomic state write
def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


# [Implementation 2] Append-only deployment evidence
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


def failed(state_dir: Path, release: str, phase: str, detail: str) -> dict[str, Any]:
    append_event(state_dir, "deployment-failed", release, f"{phase}:{detail}")
    return {"status": "failed", "phase": phase, "detail": detail}


# [Implementation 3] Environment deployment lock
@contextmanager
def deployment_lock(state_dir: Path) -> Iterator[bool]:
    lock_path = state_dir / "deployment.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    acquired = False
    try:
        os.fchmod(descriptor, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        acquired = True
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.fsync(descriptor)
        yield True
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _integer(value: Any, label: str) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    return value


def deploy(state_dir: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    state_dir.chmod(0o700)
    release = str(manifest.get("release_id", "unknown"))

    with deployment_lock(state_dir) as acquired:
        if not acquired:
            return {"status": "failed", "phase": "lock", "detail": "deployment already in progress"}

        staged_path = state_dir / "staged.json"
        current_path = state_dir / "current.json"
        try:
            # [Implementation 4] Compatibility preflight and candidate staging
            if not current_path.is_file():
                return failed(state_dir, release, "preflight", "current state missing")
            try:
                current = json.loads(current_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                return failed(state_dir, release, "preflight", f"current state invalid: {exc}")
            image = manifest.get("image")
            if manifest.get("schema_version") != 1:
                return failed(state_dir, release, "preflight", "unsupported manifest schema")
            if not isinstance(image, str) or not DIGEST.fullmatch(image):
                return failed(state_dir, release, "preflight", "image is not an exact digest")
            if manifest.get("available") is not True:
                return failed(state_dir, release, "preflight", "image unavailable")
            try:
                database_schema = _integer(current.get("db_schema"), "current db_schema")
                schema_min = _integer(manifest.get("schema_min"), "schema_min")
                schema_max = _integer(manifest.get("schema_max"), "schema_max")
                migration_target = _integer(manifest.get("migration_target"), "migration_target")
                previous_compatibility = current.get("current_compat", {})
                if not isinstance(previous_compatibility, dict):
                    raise ValueError("current_compat must be an object")
                previous_min = _integer(previous_compatibility.get("schema_min"), "previous schema_min")
                previous_max = _integer(previous_compatibility.get("schema_max"), "previous schema_max")
            except ValueError as exc:
                return failed(state_dir, release, "preflight", str(exc))
            if schema_min > schema_max or not schema_min <= database_schema <= schema_max:
                return failed(state_dir, release, "preflight", "current schema is incompatible with candidate")
            if not schema_min <= migration_target <= schema_max:
                return failed(state_dir, release, "preflight", "migration target is outside candidate range")
            if previous_min > previous_max or not previous_min <= migration_target <= previous_max:
                return failed(
                    state_dir,
                    release,
                    "preflight",
                    "migration would make automatic rollback incompatible",
                )

            append_event(state_dir, "preflight-passed", release)
            atomic_json(staged_path, {"release": release, "image": image, "phase": "starting"})
            append_event(state_dir, "candidate-staged", release)

            # The database state can advance before release publication only because
            # preflight proved that the previous release can still use the target schema.
            migrated = dict(current)
            migrated["db_schema"] = migration_target
            atomic_json(current_path, migrated)
            current = migrated
            append_event(state_dir, "migration-applied", release, f"schema={migration_target}")

            # [Implementation 5] Readiness and external smoke gates
            if manifest.get("readiness") is not True:
                staged_path.unlink(missing_ok=True)
                append_event(state_dir, "rollback-completed", release, "readiness failed; previous release retained")
                return failed(state_dir, release, "readiness", "candidate not ready")
            append_event(state_dir, "readiness-passed", release)
            if manifest.get("smoke") is not True:
                staged_path.unlink(missing_ok=True)
                append_event(state_dir, "rollback-completed", release, "smoke failed; previous release retained")
                return failed(state_dir, release, "smoke", "external smoke failed")
            append_event(state_dir, "smoke-passed", release)

            # [Implementation 6] Atomic release commit
            new_state = {
                "current": release,
                "previous": current.get("current"),
                "db_schema": migration_target,
                "current_compat": {"schema_min": schema_min, "schema_max": schema_max},
                "image": image,
            }
            atomic_json(current_path, new_state)
            staged_path.unlink(missing_ok=True)
            fsync_directory(state_dir)
            append_event(state_dir, "release-committed", release)
            return {"status": "success", "phase": "committed", "current": release}
        finally:
            staged_path.unlink(missing_ok=True)


# [Implementation 7] YAML CLI boundary
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a release manifest to a durable deployment state.")
    parser.add_argument("state_dir", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        value = yaml.safe_load(args.manifest.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        parser.error(f"cannot load manifest: {exc}")
    if not isinstance(value, dict):
        parser.error("manifest root must be a mapping")
    result = deploy(args.state_dir, value)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
