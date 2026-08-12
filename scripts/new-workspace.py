#!/usr/bin/env python3
"""Canonical learner start를 덮어쓰지 않고 exercise workspace로 복사합니다."""
from __future__ import annotations

import ctypes
import errno
import os
import shutil
import sys
import tempfile
from pathlib import Path


EXERCISE_SOURCES = {
    "exercises/01-request-and-process": "skeleton",
    "exercises/02-container": "skeleton",
    "exercises/03-compose": "skeleton",
    "exercises/04-gateway-runtime": "skeleton",
    "exercises/05-database": "skeleton",
    "exercises/06-app-bootstrap": "skeleton",
    "exercises/07-troubleshooting": "template",
    "exercises/08-production-contract": "skeleton",
    "exercises/09-host-hardening": "skeleton",
    "exercises/10-public-tls": "skeleton",
    "exercises/11-release-artifact": "skeleton",
    "exercises/12-deployment-rollback": "skeleton",
    "exercises/13-secret-rotation": "skeleton",
    "exercises/14-observability": "skeleton",
    "exercises/15-disaster-recovery": "skeleton",
    "exercises/16-capacity-and-updates": "skeleton",
    "exercises/17-incident-response": "skeleton",
    "exercises/18-production-rebuild": "skeleton",
}


class WorkspaceError(RuntimeError):
    """안전한 workspace 생성 계약을 만족하지 못했습니다."""


def _publish_no_replace(source: Path, destination: Path) -> None:
    encoded_source = os.fsencode(source)
    encoded_destination = os.fsencode(destination)
    libc = ctypes.CDLL(None, use_errno=True)

    if sys.platform == "darwin":
        function = libc.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        status = function(encoded_source, encoded_destination, 0x00000004)
    elif sys.platform.startswith("linux"):
        function = libc.renameat2
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        status = function(-100, encoded_source, -100, encoded_destination, 0x00000001)
    else:
        raise WorkspaceError(
            f"exclusive atomic publish를 지원하지 않는 플랫폼입니다: {sys.platform}"
        )

    if status:
        error_number = ctypes.get_errno()
        if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
            raise WorkspaceError(f"기존 workspace를 덮어쓰지 않습니다: {destination}")
        raise WorkspaceError(
            f"workspace를 원자적으로 공개하지 못했습니다: "
            f"{os.strerror(error_number)}"
        )


def _reject_symlinks(path: Path, label: str) -> None:
    if path.is_symlink():
        raise WorkspaceError(f"{label} symlink를 허용하지 않습니다: {path}")
    if not path.is_dir():
        raise WorkspaceError(f"{label} 디렉터리가 없습니다: {path}")
    for child in path.rglob("*"):
        if child.is_symlink():
            raise WorkspaceError(f"{label} 내부 symlink를 복사하지 않습니다: {child}")


def _relative_exercise(root: Path, raw: str) -> str:
    candidate = Path(raw)
    if any(part in {".", ".."} for part in candidate.parts):
        raise WorkspaceError(f"경로 순회 표기를 허용하지 않습니다: {raw}")
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(root)
        except ValueError as error:
            raise WorkspaceError(f"저장소 밖 exercise를 허용하지 않습니다: {raw}") from error
    relative = candidate.as_posix().rstrip("/")
    if relative not in EXERCISE_SOURCES:
        raise WorkspaceError(f"알 수 없는 exercise입니다: {raw}")
    return relative


def create_workspace(root: Path, raw_exercise: str) -> Path:
    root = root.resolve()
    relative = _relative_exercise(root, raw_exercise)
    exercise = root / relative
    source = exercise / EXERCISE_SOURCES[relative]
    destination = exercise / "workspace"
    lock = exercise / ".workspace.lock"
    temporary: Path | None = None

    if root.is_symlink() or (root / "exercises").is_symlink() or exercise.is_symlink():
        raise WorkspaceError("exercise 경로의 symlink component를 허용하지 않습니다.")
    _reject_symlinks(source, "learner start")
    if destination.exists() or destination.is_symlink():
        raise WorkspaceError(f"기존 workspace를 덮어쓰지 않습니다: {destination}")

    try:
        lock.mkdir()
    except FileExistsError as error:
        raise WorkspaceError(
            f"다른 생성 작업이 진행 중이거나 stale lock이 있습니다: {lock}"
        ) from error

    try:
        if destination.exists() or destination.is_symlink():
            raise WorkspaceError(f"기존 workspace를 덮어쓰지 않습니다: {destination}")
        temporary = Path(tempfile.mkdtemp(prefix=".workspace.tmp.", dir=exercise))
        shutil.copytree(source, temporary, dirs_exist_ok=True, copy_function=shutil.copy2)
        _publish_no_replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None and temporary.is_dir() and not temporary.is_symlink():
            shutil.rmtree(temporary)
        try:
            lock.rmdir()
        except FileNotFoundError:
            pass

    return destination


def is_safe_workspace(path: Path) -> bool:
    """Verifier가 learner path를 따라 repository 밖으로 나가지 않게 합니다."""

    if not path.is_dir() or path.is_symlink():
        return False
    try:
        return not any(child.is_symlink() for child in path.rglob("*"))
    except OSError:
        return False


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "사용법: python3 scripts/new-workspace.py exercises/NN-name",
            file=sys.stderr,
        )
        return 2
    root = Path(__file__).resolve().parents[1]
    try:
        destination = create_workspace(root, sys.argv[1])
    except (OSError, WorkspaceError) as error:
        print(f"new-workspace: {error}", file=sys.stderr)
        return 1
    print(f"작업 공간을 만들었습니다: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
