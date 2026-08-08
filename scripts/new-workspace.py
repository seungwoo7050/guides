#!/usr/bin/env python3
"""검증된 skeleton을 기존 작업을 덮어쓰지 않고 원자적으로 복사합니다."""

from __future__ import annotations

import os
import shutil
import signal
import sys
import tempfile
import time
from typing import NoReturn
from pathlib import Path

from atomic_directory_publish import publish_directory_exclusive

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"exercises/processor-model"}
staging: Path | None = None
lock: Path | None = None


def fail(message: str) -> NoReturn:
    print(f"new-workspace: {message}", file=sys.stderr)
    raise SystemExit(2)


def cleanup(*_: object) -> None:
    if staging is not None and staging.exists():
        shutil.rmtree(staging)
    if lock is not None:
        try:
            lock.rmdir()
        except FileNotFoundError:
            pass


def main() -> int:
    global staging, lock
    if len(sys.argv) != 2:
        fail("사용법: scripts/new-workspace.sh exercises/processor-model")
    raw_text = sys.argv[1]
    if raw_text == ".":
        candidate = Path.cwd()
    elif raw_text == "exercises/processor-model":
        candidate = ROOT / raw_text
    else:
        fail("path traversal·절대 경로·symlink alias는 허용하지 않습니다.")
    try:
        exercise = candidate.resolve(strict=True)
        relative = exercise.relative_to(ROOT).as_posix()
    except (FileNotFoundError, ValueError):
        fail("저장소의 허용된 exercise 경로가 아닙니다.")
    expected = ROOT / relative
    if relative not in ALLOWED or any(
        path.is_symlink()
        for path in (ROOT / "exercises", expected)
    ):
        fail("manifest에 없는 exercise 경로입니다.")
    skeleton = exercise / "skeleton"
    workspace = exercise / "workspace"
    if not skeleton.is_dir() or skeleton.is_symlink():
        fail("skeleton은 실제 디렉터리여야 합니다.")
    if workspace.exists() or workspace.is_symlink():
        fail("기존 workspace를 덮어쓰지 않습니다.")
    for path in skeleton.rglob("*"):
        if path.is_symlink():
            fail(f"skeleton symlink를 복사하지 않습니다: {path.relative_to(ROOT)}")
    lock = exercise / ".workspace-create.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        fail("다른 workspace 생성이 진행 중입니다.")
    test_pause = os.environ.get("GUIDE_WORKSPACE_TEST_PAUSE")
    if test_pause:
        time.sleep(float(test_pause))
    staging = Path(tempfile.mkdtemp(prefix=".workspace-copy.", dir=exercise))
    for source in sorted(skeleton.rglob("*")):
        target = staging / source.relative_to(skeleton)
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target, follow_symlinks=False)
        else:
            fail(f"지원하지 않는 skeleton 항목입니다: {source.relative_to(ROOT)}")
    if not any(staging.rglob("*")):
        fail("skeleton이 비어 있습니다.")
    if workspace.exists() or workspace.is_symlink():
        fail("기존 workspace를 덮어쓰지 않습니다.")
    test_before_publish = os.environ.get("GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH")
    if test_before_publish:
        time.sleep(float(test_before_publish))
    try:
        publish_directory_exclusive(staging, workspace)
    except FileExistsError:
        fail("동시에 생성된 workspace를 덮어쓰지 않습니다.")
    except (OSError, ValueError) as error:
        fail(f"workspace 원자 게시가 실패했습니다: {error}")
    staging = None
    lock.rmdir()
    lock = None
    print(f"workspace를 만들었습니다: {workspace}")
    return 0


if __name__ == "__main__":
    def interrupted(signum: int, _frame: object) -> NoReturn:
        cleanup()
        raise SystemExit(128 + signum)

    for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, interrupted)
    try:
        raise SystemExit(main())
    finally:
        cleanup()
