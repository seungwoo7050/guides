#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from dependency_receipt import DependencyReceiptError, installation_receipt
from source_manifest import SourceManifestError, build_manifest, fingerprint_manifest
from toolchain_contract import command_version

ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = ROOT / ".guide"
STATE_DIR = STATE_ROOT / "mobile-app"
MARKER = STATE_DIR / "prepared.json"


def fail(message: str) -> None:
    raise SystemExit(f"PREPARE ERROR: {message}")


def ensure_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            fail(f"state path가 실제 directory가 아닙니다: {path}")
        return
    path.mkdir(mode=0o755)


def ensure_safe_state_dir() -> None:
    ensure_directory(STATE_ROOT)
    ensure_directory(STATE_DIR)
    if MARKER.exists() or MARKER.is_symlink():
        metadata = MARKER.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            fail(f"marker가 실제 regular file이 아닙니다: {MARKER}")


def validate_existing_state_dir() -> None:
    for path in (STATE_ROOT, STATE_DIR):
        if path.is_symlink():
            fail(f"state path가 symlink입니다: {path}")
        if not path.is_dir():
            fail("먼저 repository root에서 ./prepare.sh를 실행하십시오.")
    if MARKER.is_symlink():
        fail(f"marker가 symlink입니다: {MARKER}")
    if not MARKER.is_file():
        fail("먼저 repository root에서 ./prepare.sh를 실행하십시오.")


def atomic_write_json(path: Path, value: dict[str, object]) -> None:
    ensure_safe_state_dir()
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def source_paths() -> list[Path]:
    try:
        return [entry.path for entry in build_manifest(ROOT)]
    except SourceManifestError as error:
        fail(str(error))


def fingerprint() -> tuple[str, int]:
    try:
        return fingerprint_manifest(build_manifest(ROOT))
    except SourceManifestError as error:
        fail(str(error))


def sha256(path: Path) -> str | None:
    if path.is_symlink():
        fail(f"hash 대상이 symlink입니다: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        fail(f"hash 대상이 regular file이 아닙니다: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_contract() -> dict[str, object]:
    source_sha, count = fingerprint()
    try:
        dependency = installation_receipt(ROOT)
    except DependencyReceiptError as error:
        fail(str(error))
    return {
        "schema": 3,
        "guide": "mobile-app",
        "source_sha256": source_sha,
        "source_file_count": count,
        "package_lock_sha256": sha256(ROOT / "package-lock.json"),
        "dependency_receipt": dependency,
        "node": command_version(["node", "--version"]),
        "npm": command_version(["npm", "--version"]),
        "python": sys.version.split()[0],
    }


def write_marker(current: dict[str, object]) -> None:
    atomic_write_json(
        MARKER,
        {**current, "prepared_at_utc": datetime.now(UTC).isoformat()},
    )


def check_marker(current: dict[str, object]) -> None:
    validate_existing_state_dir()
    try:
        prepared = json.loads(MARKER.read_text())
    except (OSError, json.JSONDecodeError) as error:
        fail(f"준비 marker를 읽을 수 없습니다: {error}")
    if not isinstance(prepared, dict):
        fail("준비 marker JSON이 object가 아닙니다.")
    mismatches = [key for key, value in current.items() if prepared.get(key) != value]
    if mismatches:
        details = ", ".join(
            f"{key}: prepared={prepared.get(key)!r} current={current[key]!r}"
            for key in mismatches
        )
        fail(f"prepare 이후 source/runtime이 변경됐습니다. ./prepare.sh를 다시 실행하십시오. {details}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Record or verify prepared source identity")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--digest", action="store_true")
    mode.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.digest:
        source_sha, _count = fingerprint()
        print(source_sha)
        return
    if args.check:
        # Reject an unprepared state before consulting node_modules so dependent
        # gates receive the intended preparation error rather than incidental
        # dependency errors.
        validate_existing_state_dir()
    current = current_contract()
    if args.json:
        print(json.dumps(current, ensure_ascii=False, sort_keys=True))
        return
    if args.write:
        write_marker(current)
        print(
            "PREPARED "
            f"files={current['source_file_count']} sha256={current['source_sha256']} "
            f"node={current['node']} npm={current['npm']} python={current['python']}"
        )
        return
    check_marker(current)
    print(
        "SOURCE OK "
        f"files={current['source_file_count']} sha256={current['source_sha256']} "
        f"node={current['node']} npm={current['npm']} python={current['python']}"
    )


if __name__ == "__main__":
    main()
