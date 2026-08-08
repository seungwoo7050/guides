#!/usr/bin/env python3
"""Publish a sibling directory atomically without replacing an existing path."""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path
import sys

AT_FDCWD = -100
RENAME_NOREPLACE = 1
RENAME_EXCL = 0x00000004


def publish_directory_exclusive(source: Path, destination: Path) -> None:
    source = Path(os.path.abspath(source))
    destination = Path(os.path.abspath(destination))
    if source.parent.resolve() != destination.parent.resolve():
        raise ValueError("source와 destination은 같은 디렉터리의 sibling이어야 합니다")
    if not source.is_dir() or source.is_symlink():
        raise ValueError("source는 실제 디렉터리여야 합니다")
    if os.path.lexists(destination):
        raise FileExistsError(errno.EEXIST, "destination이 이미 존재합니다", destination)

    library = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin":
        rename_exclusive = library.renamex_np
        rename_exclusive.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        rename_exclusive.restype = ctypes.c_int
        result = rename_exclusive(source_bytes, destination_bytes, RENAME_EXCL)
    elif sys.platform.startswith("linux"):
        try:
            rename_exclusive = library.renameat2
        except AttributeError as error:
            raise OSError(errno.ENOSYS, "renameat2(RENAME_NOREPLACE)를 지원하지 않습니다") from error
        rename_exclusive.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename_exclusive.restype = ctypes.c_int
        result = rename_exclusive(
            AT_FDCWD,
            source_bytes,
            AT_FDCWD,
            destination_bytes,
            RENAME_NOREPLACE,
        )
    else:
        raise OSError(errno.ENOSYS, f"exclusive directory rename을 지원하지 않는 OS입니다: {sys.platform}")

    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise FileExistsError(error_number, "destination이 이미 존재합니다", destination)
        raise OSError(error_number, os.strerror(error_number), destination)


def main() -> int:
    if len(sys.argv) != 3:
        print("사용법: atomic_directory_publish.py <staging> <workspace>", file=sys.stderr)
        return 2
    try:
        publish_directory_exclusive(Path(sys.argv[1]), Path(sys.argv[2]))
    except FileExistsError:
        print(f"기존 workspace를 덮어쓰지 않습니다: {sys.argv[2]}", file=sys.stderr)
        return 3
    except (OSError, ValueError) as error:
        print(f"workspace 원자 게시 실패: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
