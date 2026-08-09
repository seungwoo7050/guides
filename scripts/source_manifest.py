#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import shutil
import stat
from dataclasses import dataclass
from pathlib import Path


class SourceManifestError(RuntimeError):
    pass


# These are exact repository-relative generated state boundaries, not basename
# rules and not Git ignore rules. Add a path only for an output that the
# repository's declared tooling can actually create there. In particular, the
# TypeScript-only packages use `tsc --noEmit`, so names such as `android`, `ios`,
# `dist`, and `artifacts` remain source inputs below those packages.
PACKAGE_ROOTS = {
    Path("exercises/field-notes/fault-server"),
    Path("exercises/field-notes/lifecycle-engine"),
    Path("exercises/field-notes/reference"),
    Path("exercises/field-notes/release-contract"),
    Path("exercises/field-notes/shared"),
    Path("exercises/field-notes/skeleton"),
    Path("exercises/field-notes/sync-engine"),
}
EXPO_APP_ROOTS = {
    Path("exercises/field-notes/reference"),
    Path("exercises/field-notes/skeleton"),
}
COMMON_PACKAGE_GENERATED_CHILDREN = {Path("coverage"), Path("node_modules")}
EXPO_APP_GENERATED_CHILDREN = {Path(".expo"), Path("android"), Path("dist"), Path("ios")}
GENERATED_ROOT_PATHS = {
    Path(".git"),
    Path(".guide"),
    Path("coverage"),
    Path("node_modules"),
    Path("exercises/field-notes/workspace"),
    Path("scripts/__pycache__"),
    Path("scripts/tests/__pycache__"),
    *(
        package / child
        for package in PACKAGE_ROOTS
        for child in COMMON_PACKAGE_GENERATED_CHILDREN
    ),
    *(
        package / child
        for package in EXPO_APP_ROOTS
        for child in EXPO_APP_GENERATED_CHILDREN
    ),
}
GENERATED_FILE_NAMES = {".DS_Store"}
GENERATED_FILE_SUFFIXES = {".pyc", ".tsbuildinfo"}


@dataclass(frozen=True)
class SourceEntry:
    path: Path
    relative: Path
    mode: int
    size: int
    device: int
    inode: int


def _is_generated_directory(relative: Path) -> bool:
    return relative in GENERATED_ROOT_PATHS


def _is_generated_file(relative: Path) -> bool:
    return relative.name in GENERATED_FILE_NAMES or relative.suffix in GENERATED_FILE_SUFFIXES


def _metadata(path: Path) -> os.stat_result:
    try:
        return path.lstat()
    except FileNotFoundError as error:
        raise SourceManifestError(f"source entry가 scan 중 사라졌습니다: {path}") from error


def build_manifest(root: Path) -> tuple[SourceEntry, ...]:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise SourceManifestError(f"source root가 directory가 아닙니다: {root}")

    entries: list[SourceEntry] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError as error:
            raise SourceManifestError(f"source directory를 읽지 못했습니다: {directory}: {error}") from error
        for path in children:
            relative = path.relative_to(root)
            metadata = _metadata(path)
            if stat.S_ISLNK(metadata.st_mode):
                try:
                    target = os.readlink(path)
                except OSError:
                    target = "<unreadable>"
                raise SourceManifestError(f"source symlink는 허용하지 않습니다: {relative} -> {target}")
            if stat.S_ISDIR(metadata.st_mode):
                if _is_generated_directory(relative):
                    continue
                pending.append(path)
                continue
            if stat.S_ISREG(metadata.st_mode):
                if relative in GENERATED_ROOT_PATHS or _is_generated_file(relative):
                    continue
                entries.append(
                    SourceEntry(
                        path=path,
                        relative=relative,
                        mode=stat.S_IMODE(metadata.st_mode),
                        size=metadata.st_size,
                        device=metadata.st_dev,
                        inode=metadata.st_ino,
                    )
                )
                continue
            raise SourceManifestError(
                f"regular file/directory가 아닌 source entry는 허용하지 않습니다: {relative}"
            )
    return tuple(sorted(entries, key=lambda entry: entry.relative.as_posix()))


def _open_entry(entry: SourceEntry):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(entry.path, flags)
    except OSError as error:
        raise SourceManifestError(f"source file을 안전하게 열지 못했습니다: {entry.relative}: {error}") from error
    metadata = os.fstat(descriptor)
    identity = (metadata.st_dev, metadata.st_ino, metadata.st_size)
    expected = (entry.device, entry.inode, entry.size)
    if not stat.S_ISREG(metadata.st_mode) or identity != expected:
        os.close(descriptor)
        raise SourceManifestError(f"source file이 scan 뒤 변경됐습니다: {entry.relative}")
    return os.fdopen(descriptor, "rb")


def fingerprint_manifest(entries: tuple[SourceEntry, ...]) -> tuple[str, int]:
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(
            entry.relative.as_posix().encode()
            + b"\0file\0"
            + oct(entry.mode).encode()
            + b"\0"
            + str(entry.size).encode()
            + b"\0"
        )
        read = 0
        with _open_entry(entry) as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                read += len(chunk)
        if read != entry.size:
            raise SourceManifestError(f"source file 크기가 read 중 변경됐습니다: {entry.relative}")
        digest.update(b"\0")
    return digest.hexdigest(), len(entries)


def entries_under(
    entries: tuple[SourceEntry, ...], relative_root: Path
) -> tuple[SourceEntry, ...]:
    if relative_root.is_absolute() or ".." in relative_root.parts:
        raise SourceManifestError(f"source subset path가 상대 경로가 아닙니다: {relative_root}")
    return tuple(
        entry for entry in entries if entry.relative.is_relative_to(relative_root)
    )


def copy_source_subset(
    root: Path,
    relative_root: Path,
    destination: Path,
    *,
    entries: tuple[SourceEntry, ...] | None = None,
) -> int:
    root = root.resolve(strict=True)
    source = root / relative_root
    source_metadata = _metadata(source)
    if stat.S_ISLNK(source_metadata.st_mode) or not stat.S_ISDIR(source_metadata.st_mode):
        raise SourceManifestError(f"source subset이 실제 directory가 아닙니다: {relative_root}")
    manifest = entries if entries is not None else build_manifest(root)
    subset = entries_under(manifest, relative_root)
    if destination.exists() or destination.is_symlink():
        raise SourceManifestError(f"copy destination이 이미 존재합니다: {destination}")
    destination.mkdir(parents=True, mode=0o755)
    for entry in subset:
        relative = entry.relative.relative_to(relative_root)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with _open_entry(entry) as source_handle, target.open("xb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle, length=1024 * 1024)
        os.chmod(target, entry.mode)
    return len(subset)


def read_entry_text(entry: SourceEntry, *, errors: str = "strict") -> str:
    with _open_entry(entry) as handle:
        data = handle.read()
    if len(data) != entry.size:
        raise SourceManifestError(f"source file 크기가 read 중 변경됐습니다: {entry.relative}")
    return data.decode("utf-8", errors=errors)
