#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXERCISE = Path("exercises/02-c-language/03-int-vector")


def fail(message: str) -> None:
    print(f"workspace 검사 실패: {message}", file=sys.stderr)
    raise SystemExit(1)


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run(repository: Path, argument: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", "scripts/new-workspace.sh", argument],
        cwd=repository,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def require_failure(repository: Path, argument: str, label: str) -> None:
    result = run(repository, argument)
    if result.returncode == 0:
        fail(f"거부해야 할 입력을 허용했습니다: {label}")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="guide-c-workspace-") as temporary:
        repository = Path(temporary) / "repository"
        shutil.copytree(
            ROOT,
            repository,
            symlinks=True,
            ignore=shutil.ignore_patterns(
                ".git", "build", "workspace", ".workspace.*", "__pycache__",
                ".guide-prepare.env"
            ),
        )
        exercise = repository / EXERCISE
        skeleton = exercise / "skeleton"
        workspace = exercise / "workspace"
        source_before = fingerprint(skeleton)

        created = run(repository, EXERCISE.as_posix())
        if created.returncode != 0:
            fail(f"정상 workspace 생성이 실패했습니다: {created.stderr.strip()}")
        if not workspace.is_dir() or workspace.is_symlink():
            fail("workspace가 실제 디렉터리로 생성되지 않았습니다")
        if fingerprint(workspace) != source_before:
            fail("workspace가 skeleton과 byte-for-byte 일치하지 않습니다")

        workspace_before = fingerprint(workspace)
        require_failure(repository, EXERCISE.as_posix(), "기존 workspace non-overwrite")
        if fingerprint(workspace) != workspace_before:
            fail("두 번째 생성 시 기존 workspace가 변경되었습니다")
        if fingerprint(skeleton) != source_before:
            fail("workspace 생성이 skeleton을 변경했습니다")

        require_failure(repository, "exercises/../README.md", "경로 순회")
        os.symlink(exercise, repository / "exercises" / "linked-exercise")
        require_failure(repository, "exercises/linked-exercise", "exercise symlink")

        shutil.copy2(
            exercise / "reference/src/int_vector.c",
            workspace / "src/int_vector.c",
        )
        learner_test = subprocess.run(
            ["make", "exercise-test"],
            cwd=exercise,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if learner_test.returncode != 0:
            fail("완성 workspace의 기본 exercise-test가 실패했습니다")
        sanitize_plan = subprocess.run(
            ["make", "-n", "sanitize"],
            cwd=exercise,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if sanitize_plan.returncode != 0 or "workspace/src/int_vector.c" not in sanitize_plan.stdout:
            fail("기본 sanitize가 learner workspace를 선택하지 않습니다")
        if "reference/src/int_vector.c" in sanitize_plan.stdout:
            fail("learner sanitize가 reference source를 함께 검사합니다")

        shutil.rmtree(workspace)
        os.symlink(exercise / "README.md", skeleton / "linked-source")
        require_failure(repository, EXERCISE.as_posix(), "skeleton 내부 symlink")

    print("workspace 안전성·learner 기본 검증 검사 통과")


if __name__ == "__main__":
    main()
