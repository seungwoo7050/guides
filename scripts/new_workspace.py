#!/usr/bin/env python3
"""Create one non-overwriting learner workspace from a canonical track."""

from __future__ import annotations

import argparse
import ctypes
import errno
import os
import shutil
import sys
import tempfile
from pathlib import Path

from manage_artifacts import is_generated_dir_name, is_generated_file


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT / ".workspace"
TRACKS = {
    "modern": (ROOT / "exercises/01-modern-cpp", WORKSPACE_ROOT / "01-modern-cpp"),
    "cpp98": (
        ROOT / "exercises/02-cpp98-systems",
        WORKSPACE_ROOT / "02-cpp98-systems",
    ),
}


def publish_noreplace(source: Path, destination: Path) -> None:
    """Atomically publish a directory without replacing any existing path."""

    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)

    if sys.platform.startswith("linux"):
        try:
            rename = libc.renameat2
        except AttributeError as error:
            raise RuntimeError("renameat2(RENAME_NOREPLACE)를 지원하지 않습니다") from error
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(-100, source_bytes, -100, destination_bytes, 1)
    elif sys.platform == "darwin":
        try:
            rename = libc.renamex_np
        except AttributeError as error:
            raise RuntimeError("renamex_np(RENAME_EXCL)를 지원하지 않습니다") from error
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(source_bytes, destination_bytes, 0x00000004)
    else:
        raise RuntimeError(
            f"atomic no-replace publish를 지원하지 않는 platform입니다: {sys.platform}"
        )

    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(
            f"기존 workspace를 덮어쓰지 않습니다: "
            f"{destination.relative_to(ROOT)}"
        )
    raise OSError(error_number, os.strerror(error_number), destination)


def reject_symlinks(root: Path) -> None:
    for current_text, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current = Path(current_text)
        for name in [*directory_names, *file_names]:
            path = current / name
            if path.is_symlink():
                raise RuntimeError(
                    f"workspace source에는 symlink를 허용하지 않습니다: "
                    f"{path.relative_to(ROOT)}"
                )


def make_ignore(source_root: Path):
    """Return a copytree filter whose executable test is scoped to the source."""

    def ignore_generated(directory: str, names: list[str]) -> set[str]:
        current = Path(directory)
        ignored: set[str] = set()
        for name in names:
            path = current / name
            if name == ".workspace" or is_generated_dir_name(name):
                ignored.add(name)
            elif path.is_file() and is_generated_file(path, source_root):
                ignored.add(name)
        return ignored

    return ignore_generated


def create_workspace(track: str) -> Path:
    source, destination = TRACKS[track]
    if not source.is_dir():
        raise RuntimeError(f"canonical track이 없습니다: {source.relative_to(ROOT)}")

    if WORKSPACE_ROOT.is_symlink():
        raise RuntimeError(".workspace가 symlink이므로 중단합니다")
    WORKSPACE_ROOT.mkdir(mode=0o755, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(
            f"기존 workspace를 덮어쓰지 않습니다: {destination.relative_to(ROOT)}"
        )

    lock = WORKSPACE_ROOT / f".{destination.name}.lock"
    descriptor: int | None = None
    owns_lock = False
    staging: Path | None = None
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        owns_lock = True
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(
                f"기존 workspace를 덮어쓰지 않습니다: {destination.relative_to(ROOT)}"
            )

        reject_symlinks(source)
        staging = Path(
            tempfile.mkdtemp(prefix=f".{destination.name}.", dir=WORKSPACE_ROOT)
        )
        staging.rmdir()
        shutil.copytree(source, staging, symlinks=False, ignore=make_ignore(source))

        # The lock serializes supported creators; the platform's exclusive
        # rename also refuses an independently created destination atomically.
        publish_noreplace(staging, destination)
        staging = None
        return destination
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
        if descriptor is not None:
            os.close(descriptor)
        if owns_lock:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="canonical skeleton을 보존하며 learner workspace를 생성합니다."
    )
    parser.add_argument("track", choices=sorted(TRACKS))
    args = parser.parse_args()

    try:
        destination = create_workspace(args.track)
    except (FileExistsError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(destination.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
