#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
FINGERPRINT_VERSION = 2
IGNORE_DIRS = {".git", ".guide", ".workspace", "__pycache__"}
IGNORE_SUFFIXES = {".pyc", ".pyo", ".log"}
IGNORE_FILES = {".DS_Store"}
HEX_SHA256 = re.compile(r"[0-9a-f]{64}")


class FingerprintError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _field(digest: "hashlib._Hash", value: bytes) -> None:
    """Hash an unambiguous length-prefixed byte field."""

    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _ignored_file(relative: Path, metadata: os.stat_result) -> bool:
    return stat.S_ISREG(metadata.st_mode) and (
        relative.name in IGNORE_FILES or relative.suffix in IGNORE_SUFFIXES
    )


def _entries(root: Path, *, apply_source_ignores: bool) -> Iterator[tuple[Path, Path, os.stat_result]]:
    """Yield regular files and links without following directory symlinks."""

    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as error:
            raise FingerprintError("E_READ", f"directory를 읽을 수 없습니다: {directory}: {error}") from error
        directories: list[Path] = []
        for path in children:
            relative = path.relative_to(root)
            try:
                metadata = path.lstat()
            except OSError as error:
                raise FingerprintError("E_READ", f"entry metadata를 읽을 수 없습니다: {path}: {error}") from error
            if stat.S_ISDIR(metadata.st_mode):
                if apply_source_ignores and path.name in IGNORE_DIRS:
                    continue
                directories.append(path)
                continue
            if apply_source_ignores and _ignored_file(relative, metadata):
                continue
            if stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
                yield path, relative, metadata
                continue
            raise FingerprintError(
                "E_SPECIAL_FILE",
                f"regular file·directory·symlink가 아닌 source entry입니다: {relative.as_posix()}",
            )
        pending.extend(reversed(directories))


def fingerprint_tree(
    root: Path,
    *,
    apply_source_ignores: bool,
    reject_symlinks: bool,
    label: str,
) -> str:
    root = root.absolute()
    digest = hashlib.sha256()
    _field(digest, f"cloud-computing-{label}-v{FINGERPRINT_VERSION}".encode("ascii"))

    if not root.exists() and not root.is_symlink():
        _field(digest, b"ABSENT")
        return digest.hexdigest()
    try:
        root_metadata = root.lstat()
    except OSError as error:
        raise FingerprintError("E_ROOT", f"fingerprint root를 읽을 수 없습니다: {root}: {error}") from error
    if stat.S_ISLNK(root_metadata.st_mode):
        raise FingerprintError("E_ROOT_SYMLINK", f"fingerprint root는 symlink일 수 없습니다: {root}")
    if not stat.S_ISDIR(root_metadata.st_mode):
        raise FingerprintError("E_ROOT", f"fingerprint root는 directory여야 합니다: {root}")

    _field(digest, b"PRESENT")
    entries = sorted(
        _entries(root, apply_source_ignores=apply_source_ignores),
        key=lambda item: item[1].as_posix(),
    )
    for path, relative, metadata in entries:
        relative_bytes = os.fsencode(relative.as_posix())
        mode_bytes = f"{stat.S_IMODE(metadata.st_mode):04o}".encode("ascii")
        if stat.S_ISLNK(metadata.st_mode):
            try:
                target = os.fsencode(os.readlink(path))
            except OSError as error:
                raise FingerprintError("E_READ", f"symlink target을 읽을 수 없습니다: {relative}") from error
            if reject_symlinks:
                rendered = os.fsdecode(target)
                raise FingerprintError(
                    "E_SOURCE_SYMLINK",
                    f"source symlink는 허용하지 않습니다: {relative.as_posix()} -> {rendered}",
                )
            _field(digest, b"L")
            _field(digest, relative_bytes)
            _field(digest, mode_bytes)
            _field(digest, target)
            continue

        try:
            data = path.read_bytes()
        except OSError as error:
            raise FingerprintError("E_READ", f"source file을 읽을 수 없습니다: {relative}: {error}") from error
        _field(digest, b"F")
        _field(digest, relative_bytes)
        _field(digest, mode_bytes)
        _field(digest, data)
    return digest.hexdigest()


def source_fingerprint(root: Path, *, reject_symlinks: bool = True) -> str:
    return fingerprint_tree(
        root,
        apply_source_ignores=True,
        reject_symlinks=reject_symlinks,
        label="source",
    )


def workspace_fingerprint(repository_root: Path) -> str:
    """Fingerprint all learner work without following links or changing it."""

    return fingerprint_tree(
        repository_root.absolute() / ".workspace",
        apply_source_ignores=False,
        reject_symlinks=False,
        label="workspace",
    )


def _contained_regular_file(root: Path, candidate: Path, label: str) -> Path:
    root = root.absolute()
    unresolved = candidate if candidate.is_absolute() else root / candidate
    unresolved = unresolved.absolute()
    try:
        relative = unresolved.relative_to(root)
    except ValueError as error:
        raise FingerprintError("E_MARKER_PATH", f"{label}가 repository 밖입니다: {candidate}") from error

    current = root
    for component in relative.parts:
        current = current / component
        try:
            metadata = current.lstat()
        except FileNotFoundError as error:
            raise FingerprintError("E_MARKER_MISSING", f"{label}가 없습니다: {candidate}") from error
        if stat.S_ISLNK(metadata.st_mode):
            raise FingerprintError("E_MARKER_SYMLINK", f"{label} 경로는 symlink일 수 없습니다: {current}")
    if not stat.S_ISREG(unresolved.lstat().st_mode):
        raise FingerprintError("E_MARKER_PATH", f"{label}는 regular file이어야 합니다: {candidate}")
    return unresolved


def validate_marker(root: Path, marker_path: Path) -> str:
    marker = _contained_regular_file(root, marker_path, "prepare marker")
    try:
        value = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FingerprintError("E_MARKER_JSON", f"prepare marker를 읽을 수 없습니다: {error}") from error
    if not isinstance(value, dict):
        raise FingerprintError("E_MARKER_SCHEMA", "prepare marker 최상위 값은 object여야 합니다.")
    if value.get("schema_version") != 2:
        raise FingerprintError("E_MARKER_SCHEMA", "prepare marker schema_version은 2여야 합니다.")
    if value.get("fingerprint_version") != FINGERPRINT_VERSION:
        raise FingerprintError(
            "E_MARKER_SCHEMA",
            f"prepare marker fingerprint_version은 {FINGERPRINT_VERSION}여야 합니다.",
        )
    if value.get("guide") != "cloud-computing":
        raise FingerprintError("E_MARKER_SCHEMA", "prepare marker guide가 cloud-computing이 아닙니다.")
    expected = value.get("source_fingerprint")
    if not isinstance(expected, str) or HEX_SHA256.fullmatch(expected) is None:
        raise FingerprintError("E_MARKER_SCHEMA", "prepare marker source_fingerprint가 유효하지 않습니다.")
    if value.get("network_required") is not False or value.get("required_external_services") != []:
        raise FingerprintError("E_MARKER_SCHEMA", "prepare marker의 no-network/no-service 계약이 유효하지 않습니다.")
    actual = source_fingerprint(root, reject_symlinks=True)
    if actual != expected:
        raise FingerprintError(
            "E_SOURCE_CHANGED",
            "prepare 이후 source가 변경되었습니다. ./prepare.sh를 다시 실행하세요.\n"
            f"expected={expected}\nactual={actual}",
        )
    return actual


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cloud-computing source/workspace fingerprint v2")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--scope", choices=("source", "workspace"), default="source")
    parser.add_argument("--allow-source-symlinks", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--check-marker", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.absolute()
    try:
        if args.check_marker is not None:
            print(f"SOURCE OK: {validate_marker(root, args.check_marker)}")
        elif args.scope == "workspace":
            print(workspace_fingerprint(root))
        else:
            print(source_fingerprint(root, reject_symlinks=not args.allow_source_symlinks))
    except FingerprintError as error:
        print(f"FINGERPRINT ERROR [{error.code}]: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
