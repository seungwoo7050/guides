#!/usr/bin/env python3
"""workspace 생성기의 경계·symlink·덮어쓰기 계약을 검사합니다."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import stat
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISE = "exercises/processor-model"


def copy_source(destination: Path) -> None:
    shutil.copytree(
        ROOT, destination, symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".guide", "workspace", "build", "__pycache__", "*.pyc"),
    )


def run(root: Path, argument: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(root / "scripts/new-workspace.sh"), argument], cwd=root,
        check=False, capture_output=True, text=True, timeout=20,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-architecture-workspace-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        created = run(root, EXERCISE)
        if created.returncode != 0 or not (root / EXERCISE / "workspace/processor-model.py").is_file():
            raise AssertionError(created.stdout + created.stderr)
        sentinel = root / EXERCISE / "workspace/sentinel"
        sentinel.write_text("keep\n", encoding="utf-8")
        repeated = run(root, EXERCISE)
        if repeated.returncode == 0 or sentinel.read_text(encoding="utf-8") != "keep\n":
            raise AssertionError("기존 workspace 덮어쓰기를 거부하지 못했습니다.")
        traversal = run(root, "exercises/../docs")
        if traversal.returncode == 0 or "path traversal" not in traversal.stderr:
            raise AssertionError("path traversal을 거부하지 못했습니다.")
        print("[PASS] workspace create/no-overwrite/traversal")
        canonical_traversal = run(root, "exercises/../exercises/processor-model")
        if canonical_traversal.returncode == 0:
            raise AssertionError("canonical path traversal을 허용했습니다.")
    with tempfile.TemporaryDirectory(prefix="guide-architecture-symlink-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        (root / EXERCISE / "skeleton/dangling").symlink_to("missing")
        rejected = run(root, EXERCISE)
        if rejected.returncode == 0 or "symlink" not in rejected.stderr:
            raise AssertionError("skeleton symlink를 거부하지 못했습니다.")
        print("[PASS] workspace skeleton symlink rejection")
    with tempfile.TemporaryDirectory(prefix="guide-architecture-alias-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        (root / "exercises/processor-alias").symlink_to("processor-model")
        alias = run(root, "exercises/processor-alias")
        if alias.returncode == 0:
            raise AssertionError("exercise symlink alias를 허용했습니다.")
        print("[PASS] workspace symlink alias rejection")
    with tempfile.TemporaryDirectory(prefix="guide-architecture-workspace-signal-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        environment = os.environ.copy()
        environment["GUIDE_WORKSPACE_TEST_PAUSE"] = "10"
        process = subprocess.Popen(
            [str(root / "scripts/new-workspace.sh"), EXERCISE],
            cwd=root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        lock = root / EXERCISE / ".workspace-create.lock"
        deadline = time.monotonic() + 5
        while not lock.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if not lock.exists():
            process.kill()
            raise AssertionError("중단 검사 전에 workspace lock을 관찰하지 못했습니다.")
        process.terminate()
        process.communicate(timeout=5)
        leftovers = list((root / EXERCISE).glob(".workspace-copy.*"))
        if lock.exists() or leftovers or (root / EXERCISE / "workspace").exists():
            raise AssertionError("signal 중단 뒤 workspace 임시 상태가 남았습니다.")
        recovered = run(root, EXERCISE)
        if recovered.returncode != 0:
            raise AssertionError("signal 중단 뒤 workspace를 다시 만들 수 없습니다.")
        print("[PASS] workspace interruption cleanup/retry")
    with tempfile.TemporaryDirectory(prefix="guide-architecture-workspace-race-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        environment = os.environ.copy()
        environment["GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH"] = "10"
        process = subprocess.Popen(
            [str(root / "scripts/new-workspace.sh"), EXERCISE],
            cwd=root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        exercise = root / EXERCISE
        deadline = time.monotonic() + 5
        while process.poll() is None and time.monotonic() < deadline:
            if list(exercise.glob(".workspace-copy.*/processor-model.py")):
                break
            time.sleep(0.02)
        else:
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            raise AssertionError("원자 게시 경쟁 검사에서 완성된 staging을 관찰하지 못했습니다.")
        workspace = exercise / "workspace"
        workspace.mkdir()
        output = process.communicate(timeout=15)
        if process.returncode == 0:
            raise AssertionError("동시에 생긴 workspace를 덮어썼습니다.")
        if list(workspace.iterdir()):
            raise AssertionError("경쟁 상대의 빈 workspace에 skeleton을 썼습니다.")
        if list(exercise.glob(".workspace-copy.*")) or (exercise / ".workspace-create.lock").exists():
            raise AssertionError("경쟁 실패 뒤 임시 상태가 남았습니다.")
        print("[PASS] workspace exclusive publish race rejection")
    with tempfile.TemporaryDirectory(prefix="guide-architecture-clean-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        learner = root / EXERCISE / "workspace/__pycache__/learner.pyc"
        prepared = root / ".guide/computer-architecture/__pycache__/prepared.pyc"
        generated = root / "scripts/__pycache__/generated.pyc"
        for path, payload in ((learner, b"learner"), (prepared, b"prepared"), (generated, b"generated")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            path.chmod(0o640)
        cleaned = subprocess.run(["make", "clean"], cwd=root, capture_output=True, text=True, check=False)
        if cleaned.returncode:
            raise AssertionError(cleaned.stdout + cleaned.stderr)
        if learner.read_bytes() != b"learner" or stat.S_IMODE(learner.stat().st_mode) != 0o640:
            raise AssertionError("clean이 learner workspace를 변경했습니다.")
        if prepared.read_bytes() != b"prepared" or stat.S_IMODE(prepared.stat().st_mode) != 0o640:
            raise AssertionError("clean이 .guide 준비 상태를 변경했습니다.")
        if generated.exists():
            raise AssertionError("clean이 알려진 source cache를 제거하지 않았습니다.")
        print("[PASS] clean preserves workspace/.guide and removes known source cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
