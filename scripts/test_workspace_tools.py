#!/usr/bin/env python3
"""Exercise workspace path, overwrite, symlink, manifest, and interruption safety."""

from __future__ import annotations

import os
import shutil
import subprocess
import stat
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_repository(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".guide", "workspace", "__pycache__", "*.pyc"),
    )


def run(root: Path, argument: str, *, interrupt: bool = False) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if interrupt:
        environment["GUIDE_WORKSPACE_TEST_INTERRUPT"] = "1"
    return subprocess.run(
        ["sh", "scripts/new-workspace.sh", argument],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def require_failure(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        raise AssertionError(f"{label} unexpectedly succeeded")


def run_make(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-cn-workspace-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        require_failure(run_make(root, "protocol-check"), "protocol learner check without workspace")
        require_failure(run_make(root, "path-diagnosis-check"), "path learner check without workspace")
        protocol_reference = run_make(root, "protocol-check", "EXERCISE_IMPL=reference")
        if protocol_reference.returncode:
            raise AssertionError(protocol_reference.stdout + protocol_reference.stderr)
        path_reference = run_make(root, "path-diagnosis-check", "PATH_EXERCISE_IMPL=reference")
        if path_reference.returncode:
            raise AssertionError(path_reference.stdout + path_reference.stderr)

    with tempfile.TemporaryDirectory(prefix="guide-cn-workspace-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        exercise = root / "exercises/protocol-inspector"
        result = run(root, "exercises/protocol-inspector")
        if result.returncode or not (exercise / "workspace/protocol_inspector/checksum.py").is_file():
            raise AssertionError(result.stdout + result.stderr)
        require_failure(run(root, "exercises/protocol-inspector"), "existing workspace")

    with tempfile.TemporaryDirectory(prefix="guide-cn-workspace-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        require_failure(run(root, "../outside"), "path traversal")
        (root / "exercises/protocol-inspector/workspace").symlink_to(Path(temporary) / "outside")
        require_failure(run(root, "exercises/protocol-inspector"), "workspace symlink")

    with tempfile.TemporaryDirectory(prefix="guide-cn-workspace-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        (root / "exercises/protocol-inspector/skeleton/unlisted.py").write_text("x = 1\n", encoding="utf-8")
        require_failure(run(root, "exercises/protocol-inspector"), "unmanifested skeleton file")

    with tempfile.TemporaryDirectory(prefix="guide-cn-workspace-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        result = run(root, "exercises/path-diagnosis", interrupt=True)
        require_failure(result, "interrupted copy")
        exercise = root / "exercises/path-diagnosis"
        if (exercise / "workspace").exists() or list(exercise.glob(".workspace-copy.*")) or (exercise / ".workspace-create.lock").exists():
            raise AssertionError("interrupted workspace left partial state")

    with tempfile.TemporaryDirectory(prefix="guide-cn-workspace-race-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        exercise = root / "exercises/protocol-inspector"
        environment = os.environ.copy()
        environment["GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH"] = "10"
        process = subprocess.Popen(
            ["sh", "scripts/new-workspace.sh", "exercises/protocol-inspector"],
            cwd=root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        deadline = time.monotonic() + 5
        while process.poll() is None and time.monotonic() < deadline:
            if list(exercise.glob(".workspace-copy.*/protocol_inspector/checksum.py")):
                break
            time.sleep(0.02)
        else:
            process.terminate()
            process.communicate(timeout=5)
            raise AssertionError("exclusive publish race staging was not observed")
        workspace = exercise / "workspace"
        workspace.mkdir()
        output = process.communicate(timeout=15)
        if process.returncode == 0:
            raise AssertionError("concurrent destination creation was overwritten")
        if list(workspace.iterdir()):
            raise AssertionError("concurrent empty workspace received staged files")
        if list(exercise.glob(".workspace-copy.*")) or (exercise / ".workspace-create.lock").exists():
            raise AssertionError("destination race left temporary workspace state")

    with tempfile.TemporaryDirectory(prefix="guide-cn-clean-") as temporary:
        root = Path(temporary) / "repo"
        copy_repository(root)
        learner = root / "exercises/protocol-inspector/workspace/__pycache__/learner.pyc"
        prepared = root / ".guide/computer-networks/__pycache__/prepared.pyc"
        generated = root / "scripts/__pycache__/generated.pyc"
        for path, payload in ((learner, b"learner"), (prepared, b"prepared"), (generated, b"generated")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            path.chmod(0o640)
        cleaned = subprocess.run(["make", "clean"], cwd=root, capture_output=True, text=True, check=False)
        if cleaned.returncode:
            raise AssertionError(cleaned.stdout + cleaned.stderr)
        if learner.read_bytes() != b"learner" or stat.S_IMODE(learner.stat().st_mode) != 0o640:
            raise AssertionError("clean changed learner workspace")
        if prepared.read_bytes() != b"prepared" or stat.S_IMODE(prepared.stat().st_mode) != 0o640:
            raise AssertionError("clean changed .guide preparation state")
        if generated.exists():
            raise AssertionError("clean did not remove known source cache")
    print("[PASS] workspace safety: success, overwrite, traversal, symlink, manifest, interruption, race, clean-preserve")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
