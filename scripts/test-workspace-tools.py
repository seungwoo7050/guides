#!/usr/bin/env python3
"""Test traversal, alias, interruption and exclusive workspace publication safety."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
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
    root = base.resolve() / "repo"
    script = root / "scripts/new-workspace.sh"
    exercise = root / "exercises/kernel-model"
    (exercise / "skeleton/kernel_model").mkdir(parents=True)
    script.parent.mkdir(parents=True)
    shutil.copy2(SOURCE_SCRIPT, script)
    script.chmod(0o755)
    publisher = root / "scripts/atomic_directory_publish.py"
    shutil.copy2(SOURCE_PUBLISHER, publisher)
    publisher.chmod(0o755)
    (exercise / "skeleton/kernel_model/lifecycle.py").write_text("VALUE = 7\n", encoding="utf-8")
    return root, script, exercise


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-os-workspace-") as temporary:
        root, script, exercise = fixture(Path(temporary))
        created = run(script, exercise)
        require(created.returncode == 0, created.stdout + created.stderr)
        workspace_file = exercise / "workspace/kernel_model/lifecycle.py"
        require(workspace_file.read_text(encoding="utf-8") == "VALUE = 7\n", "복사 결과 불일치")
        workspace_file.write_text("LEARNER = 9\n", encoding="utf-8")
        require(run(script, exercise).returncode == 2, "기존 workspace를 허용했습니다")
        require(workspace_file.read_text(encoding="utf-8") == "LEARNER = 9\n", "학습자 파일 덮어쓰기")

        outside = root / "outside"
        (outside / "skeleton").mkdir(parents=True)
        (outside / "skeleton/value.py").write_text("x = 1\n", encoding="utf-8")
        require(run(script, outside).returncode == 2, "exercises 밖 경로 허용")

    with tempfile.TemporaryDirectory(prefix="guide-os-workspace-traversal-") as temporary:
        root, script, exercise = fixture(Path(temporary))
        (root / "unused").mkdir()
        traversal = root / "unused/../exercises/kernel-model"
        require(run(script, traversal).returncode == 2, ".. 경로 순회 표기를 허용했습니다")
        alias = root / "exercises/kernel-model-alias"
        alias.symlink_to(exercise, target_is_directory=True)
        require(run(script, alias).returncode == 2, "exercise symlink alias를 허용했습니다")
        parent_alias = root / "exercises-alias"
        parent_alias.symlink_to(root / "exercises", target_is_directory=True)
        require(run(script, parent_alias / "kernel-model").returncode == 2, "parent symlink alias를 허용했습니다")

    with tempfile.TemporaryDirectory(prefix="guide-os-workspace-link-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        target = Path(temporary).resolve() / "learner-data"
        target.mkdir()
        os.symlink(target, exercise / "workspace")
        require(run(script, exercise).returncode == 2, "workspace symlink 허용")

    with tempfile.TemporaryDirectory(prefix="guide-os-skeleton-link-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        external = Path(temporary).resolve() / "secret.py"
        external.write_text("SECRET = 1\n", encoding="utf-8")
        os.symlink(external, exercise / "skeleton/linked.py")
        require(run(script, exercise).returncode == 2, "skeleton symlink 허용")

    with tempfile.TemporaryDirectory(prefix="guide-os-workspace-signal-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        environment = os.environ.copy()
        environment["GUIDE_WORKSPACE_TEST_PAUSE"] = "10"
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
        require(run(script, exercise).returncode == 0, "중단 뒤 workspace 재시도가 실패했습니다")

    with tempfile.TemporaryDirectory(prefix="guide-os-workspace-race-") as temporary:
        _root, script, exercise = fixture(Path(temporary))
        environment = os.environ.copy()
        environment["GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH"] = "0.5"
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
            candidates = list(exercise.glob(".workspace-copy.*/kernel_model/lifecycle.py"))
            if candidates:
                staging_file = candidates[0]
                break
            time.sleep(0.02)
        require(staging_file is not None, "원자 게시 직전의 완성된 staging을 관찰하지 못했습니다")
        workspace = exercise / "workspace"
        workspace.mkdir()
        raced = workspace / "raced.txt"
        raced.write_text("preserve race winner\n", encoding="utf-8")
        stdout, stderr = process.communicate(timeout=5)
        require(process.returncode != 0, stdout + stderr)
        require(raced.read_text(encoding="utf-8") == "preserve race winner\n", "경쟁 destination을 덮어썼습니다")
        require(not list(exercise.glob(".workspace-copy.*")), "경쟁 실패 뒤 staging이 남았습니다")
        require(not (exercise / ".workspace-create.lock").exists(), "경쟁 실패 뒤 lock이 남았습니다")

    print("[PASS] workspace safety: create/no-overwrite/boundary/traversal/alias/symlink/interruption/race 10개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
