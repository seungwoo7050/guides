#!/usr/bin/env python3
"""Exercise workspace creation safety in disposable repositories."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SCRIPT = ROOT / "scripts/new-workspace.sh"
SOURCE_PUBLISHER = ROOT / "scripts/atomic_directory_publish.py"


def run(script: Path, exercise: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), str(exercise)],
        cwd=script.parents[1],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


def fixture(base: Path) -> tuple[Path, Path, Path]:
    root = base / "repo"
    script = root / "scripts/new-workspace.sh"
    exercise = root / "exercises/capstone"
    (exercise / "skeleton").mkdir(parents=True)
    script.parent.mkdir(parents=True)
    shutil.copy2(SOURCE_SCRIPT, script)
    script.chmod(0o755)
    publisher = root / "scripts/atomic_directory_publish.py"
    shutil.copy2(SOURCE_PUBLISHER, publisher)
    publisher.chmod(0o755)
    (exercise / "skeleton/algorithms.py").write_text("VALUE = 7\n", encoding="utf-8")
    return root, script, exercise


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-algorithms-workspace-") as temporary:
        root, script, exercise = fixture(Path(temporary))
        created = run(script, exercise)
        require(created.returncode == 0, created.stdout + created.stderr)
        workspace_file = exercise / "workspace/algorithms.py"
        require(workspace_file.read_text(encoding="utf-8") == "VALUE = 7\n", "복사 결과가 다릅니다")
        workspace_file.write_text("LEARNER = 9\n", encoding="utf-8")
        repeated = run(script, exercise)
        require(repeated.returncode == 2, "기존 workspace를 거부하지 않았습니다")
        require(workspace_file.read_text(encoding="utf-8") == "LEARNER = 9\n", "학습자 파일을 덮어썼습니다")

        outside = root / "outside"
        (outside / "skeleton").mkdir(parents=True)
        (outside / "skeleton/value.py").write_text("x = 1\n", encoding="utf-8")
        require(run(script, outside).returncode == 2, "exercises 밖 경로를 허용했습니다")

    with tempfile.TemporaryDirectory(prefix="guide-algorithms-workspace-link-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        target = Path(temporary) / "learner-data"
        target.mkdir()
        os.symlink(target, exercise / "workspace")
        require(run(script, exercise).returncode == 2, "workspace symlink를 허용했습니다")

    with tempfile.TemporaryDirectory(prefix="guide-algorithms-skeleton-link-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        external = Path(temporary) / "secret.py"
        external.write_text("SECRET = 1\n", encoding="utf-8")
        os.symlink(external, exercise / "skeleton/linked.py")
        require(run(script, exercise).returncode == 2, "skeleton symlink를 허용했습니다")

    with tempfile.TemporaryDirectory(prefix="guide-algorithms-workspace-signal-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        environment = os.environ.copy()
        environment["GUIDE_WORKSPACE_TEST_AFTER_LOCK_MKDIR"] = "10"
        process = subprocess.Popen(
            [str(script), str(exercise)],
            cwd=script.parents[1],
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        lock = exercise / ".workspace-create.lock"
        deadline = time.monotonic() + 5
        while not lock.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        require(lock.exists(), "중단 전에 workspace lock을 관찰하지 못했습니다")
        os.killpg(process.pid, signal.SIGTERM)
        process.communicate(timeout=5)
        require(not lock.exists(), "중단 뒤 workspace lock이 남았습니다")
        require(not (exercise / "workspace").exists(), "중단 뒤 불완전 workspace가 남았습니다")
        require(not list(exercise.glob(".workspace-copy.*")), "중단 뒤 임시 복사본이 남았습니다")
        recovered = run(script, exercise)
        require(recovered.returncode == 0, "중단 뒤 workspace 재시도가 실패했습니다")

    with tempfile.TemporaryDirectory(prefix="guide-algorithms-workspace-race-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        environment = os.environ.copy()
        environment["GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH"] = "10"
        process = subprocess.Popen(
            [str(script), str(exercise)],
            cwd=script.parents[1],
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 5
        staging_file: Path | None = None
        while process.poll() is None and time.monotonic() < deadline:
            candidates = list(exercise.glob(".workspace-copy.*/algorithms.py"))
            if candidates:
                staging_file = candidates[0]
                break
            time.sleep(0.02)
        require(staging_file is not None, "원자 게시 경쟁 검사에서 완성된 staging을 관찰하지 못했습니다")
        workspace = exercise / "workspace"
        workspace.mkdir()
        stdout, stderr = process.communicate(timeout=15)
        require(process.returncode != 0, stdout + stderr)
        require(list(workspace.iterdir()) == [], "동시에 생긴 빈 workspace를 덮어썼습니다")
        require(not list(exercise.glob(".workspace-copy.*")), "경쟁 실패 뒤 staging이 남았습니다")
        require(not (exercise / ".workspace-create.lock").exists(), "경쟁 실패 뒤 lock이 남았습니다")

    with tempfile.TemporaryDirectory(prefix="guide-algorithms-clean-") as temporary:
        repository = Path(temporary) / "repo"
        shutil.copytree(
            ROOT,
            repository,
            symlinks=True,
            ignore=shutil.ignore_patterns(".git", ".guide", "workspace", "__pycache__", "*.pyc"),
        )
        learner = repository / "exercises/07-verified-algorithms-capstone/workspace/__pycache__/learner.pyc"
        prepared = repository / ".guide/algorithms/__pycache__/prepared.pyc"
        generated = repository / "scripts/__pycache__/generated.pyc"
        for path, payload in ((learner, b"learner"), (prepared, b"prepared"), (generated, b"generated")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            path.chmod(0o640)
        cleaned = subprocess.run(["make", "clean"], cwd=repository, capture_output=True, text=True, check=False)
        require(cleaned.returncode == 0, cleaned.stdout + cleaned.stderr)
        require(learner.read_bytes() == b"learner" and stat.S_IMODE(learner.stat().st_mode) == 0o640, "clean이 learner workspace를 변경했습니다")
        require(prepared.read_bytes() == b"prepared" and stat.S_IMODE(prepared.stat().st_mode) == 0o640, "clean이 .guide 준비 상태를 변경했습니다")
        require(not generated.exists(), "clean이 알려진 source cache를 제거하지 않았습니다")

    print("[PASS] workspace safety: create/no-overwrite/boundary/symlink/interruption/race/clean-preserve 8개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
