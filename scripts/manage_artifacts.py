#!/usr/bin/env python3
"""Clean, audit, and snapshot generated guide-cpp artifacts.

Only generated build/cache products are removable. Source files, learner work,
fixtures, and documents are never removed merely because they are untracked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Iterable, Iterator

ROOT_LOG_NAMES = {"make-out.txt", "tree.txt"}
PRESERVED_DIR_NAMES = {".workspace"}
GENERATED_DIR_NAMES = {
    "build",
    "__pycache__",
    ".pytest_cache",
    ".guide-probes",
}
GENERATED_DIR_PREFIXES = ("build-",)
GENERATED_DIR_SUFFIXES = (".dSYM",)
GENERATED_SUFFIXES = {
    ".o",
    ".d",
    ".a",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".pyc",
    ".pyo",
    ".gcda",
    ".gcno",
    ".profraw",
    ".profdata",
}
BINARY_MAGICS = (
    b"\x7fELF",          # ELF executable/object/shared library
    b"!<arch>\n",        # static archive
    b"MZ",               # PE executable
    b"\xfe\xed\xfa\xce",  # Mach-O 32-bit
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",  # Mach-O 64-bit
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",  # Mach-O universal/fat
    b"\xbe\xba\xfe\xca",
)


def is_generated_dir_name(name: str) -> bool:
    return (
        name in GENERATED_DIR_NAMES
        or any(name.startswith(prefix) for prefix in GENERATED_DIR_PREFIXES)
        or any(name.endswith(suffix) for suffix in GENERATED_DIR_SUFFIXES)
    )


def has_binary_magic(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            prefix = stream.read(8)
    except (OSError, PermissionError):
        return False
    return any(prefix.startswith(magic) for magic in BINARY_MAGICS)


def is_generated_file(path: Path, root: Path) -> bool:
    if path.parent == root and path.name in ROOT_LOG_NAMES:
        return True
    if path.suffix in GENERATED_SUFFIXES:
        return True
    # Extensionless native executables are common in these exercises. The
    # format check is safer and less brittle than maintaining a filename list.
    return has_binary_magic(path)


def walk_clean_tree(root: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
    """Walk without following symlinks and prune generated/.git directories."""

    for current_text, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(current_text)
        kept: list[str] = []
        for name in directory_names:
            child = current / name
            if name == ".git" or name in PRESERVED_DIR_NAMES or is_generated_dir_name(name):
                continue
            # os.walk does not descend directory symlinks when followlinks is
            # false, but removing them from the list makes that contract clear.
            if child.is_symlink():
                continue
            kept.append(name)
        directory_names[:] = kept
        yield current, directory_names, file_names


def generated_dirs(root: Path) -> list[Path]:
    found: list[Path] = []
    for current_text, directory_names, _ in os.walk(root, topdown=True, followlinks=False):
        current = Path(current_text)
        kept: list[str] = []
        for name in directory_names:
            child = current / name
            if name == ".git":
                continue
            if name in PRESERVED_DIR_NAMES:
                continue
            if is_generated_dir_name(name):
                found.append(child)
                continue
            if child.is_symlink():
                continue
            kept.append(name)
        directory_names[:] = kept
    return sorted(found, key=lambda item: len(item.parts), reverse=True)


def generated_files(root: Path) -> Iterable[Path]:
    for current, _, file_names in walk_clean_tree(root):
        for name in file_names:
            path = current / name
            if is_generated_file(path, root):
                yield path


def collect(root: Path) -> list[Path]:
    directories = generated_dirs(root)
    files = list(generated_files(root))
    directory_roots = set(directories)
    unique: set[Path] = set(directories)
    for path in files:
        if any(parent in directory_roots for parent in path.parents):
            continue
        unique.add(path)
    return sorted(unique, key=lambda item: item.as_posix())


def remove_generated(root: Path) -> list[Path]:
    removed: list[Path] = []
    for path in generated_dirs(root):
        if path.is_symlink():
            path.unlink(missing_ok=True)
            removed.append(path)
        elif path.exists():
            shutil.rmtree(path)
            removed.append(path)
    for path in list(generated_files(root)):
        if path.is_symlink() or path.exists():
            path.unlink(missing_ok=True)
            removed.append(path)
    return removed


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot(root: Path) -> list[dict[str, object]]:
    """Return a deterministic manifest of all non-generated repository data."""

    records: list[dict[str, object]] = []
    for current_text, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(current_text)
        kept: list[str] = []
        for name in directory_names:
            child = current / name
            if name == ".git" or name in PRESERVED_DIR_NAMES or is_generated_dir_name(name):
                continue
            if child.is_symlink():
                records.append(
                    {
                        "path": child.relative_to(root).as_posix(),
                        "kind": "symlink",
                        "mode": stat.S_IMODE(child.lstat().st_mode),
                        "target": os.readlink(child),
                    }
                )
                continue
            kept.append(name)
        directory_names[:] = kept

        for name in file_names:
            path = current / name
            if is_generated_file(path, root):
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                records.append(
                    {
                        "path": relative,
                        "kind": "symlink",
                        "mode": stat.S_IMODE(path.lstat().st_mode),
                        "target": os.readlink(path),
                    }
                )
                continue
            try:
                file_stat = path.stat()
                records.append(
                    {
                        "path": relative,
                        "kind": "file",
                        "mode": stat.S_IMODE(file_stat.st_mode),
                        "size": file_stat.st_size,
                        "sha256": sha256(path),
                    }
                )
            except OSError as error:
                raise RuntimeError(f"snapshot 실패: {relative}: {error}") from error

    return sorted(records, key=lambda item: str(item["path"]))


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("clean", "audit", "list", "snapshot"))
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"ERROR: 저장소 경로가 아닙니다: {root}", file=sys.stderr)
        return 2

    if args.action == "clean":
        removed = remove_generated(root)
        print(f"생성 산출물 정리: {len(removed)}개")
        return 0

    if args.action == "snapshot":
        json.dump(snapshot(root), sys.stdout, ensure_ascii=False, sort_keys=True)
        sys.stdout.write("\n")
        return 0

    found = collect(root)
    if args.action == "list":
        for path in found:
            print(relative(path, root))
        return 0

    if found:
        print("ERROR: 생성 산출물이 남아 있습니다:", file=sys.stderr)
        for path in found:
            print(f"- {relative(path, root)}", file=sys.stderr)
        return 1

    print("생성 산출물 검사: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
