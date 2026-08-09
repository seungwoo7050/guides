#!/usr/bin/env python3
"""Exercise atomic marker publication, symlink refusal, and interruption cleanup."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from repository_state import fingerprint, index_fingerprint

ROOT = Path(__file__).resolve().parents[1]


def copy_source(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git",
            ".guide",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "workspace",
            "*.pyc",
            "*.pyo",
        ),
    )
    validator = destination / "scripts/validate.py"
    validator.write_text(
        "#!/usr/bin/env python3\nprint('fixture validator: PASS')\n",
        encoding="utf-8",
    )
    validator.chmod(0o755)


def invoke(repository: Path, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["PYTHONDONTWRITEBYTECODE"] = "1"
    if environment:
        merged.update(environment)
    return subprocess.run(
        ["bash", "prepare.sh"],
        cwd=repository,
        env=merged,
        text=True,
        capture_output=True,
        timeout=45,
        check=False,
    )


def snapshot(path: Path) -> tuple[str, int, int]:
    metadata = path.stat()
    return (
        hashlib.sha256(path.read_bytes()).hexdigest(),
        stat.S_IMODE(metadata.st_mode),
        metadata.st_size,
    )


def require_failure(result: subprocess.CompletedProcess[str], expected: str) -> None:
    output = result.stdout + result.stderr
    if result.returncode == 0 or expected not in output or "PREPARE RESULT: FAIL" not in output:
        raise AssertionError(f"prepare failure contract missing ({expected!r})\n{output}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-data-prepare-") as temporary:
        fixture = Path(temporary)
        repository = fixture / "repository"
        copy_source(repository)
        subprocess.run(["git", "init", "-q", "-b", "data-engineering", str(repository)], check=True)
        subprocess.run(["git", "-C", str(repository), "config", "user.name", "Guide Safety Test"], check=True)
        subprocess.run(
            ["git", "-C", str(repository), "config", "user.email", "guide-safety@example.invalid"],
            check=True,
        )
        subprocess.run(["git", "-C", str(repository), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(repository), "commit", "-q", "-m", "fixture"], check=True)
        learner = repository / "exercises/01-contracts-and-records/01-schema-evolution/workspace"
        learner.mkdir()
        (learner / "answer.py").write_text("learner\n", encoding="utf-8")
        (learner / "answer.py").chmod(0o640)

        source_before = fingerprint(repository, "source")
        workspace_before = fingerprint(repository, "workspace")
        index_before = index_fingerprint(repository)
        baseline = invoke(repository)
        if baseline.returncode != 0:
            raise AssertionError(baseline.stdout + baseline.stderr)
        marker = repository / ".guide/data-engineering/prepared.json"
        metadata = marker.lstat()
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_nlink != 1:
            raise AssertionError("prepared marker is not a single 0600 regular file")
        payload = json.loads(marker.read_text(encoding="utf-8"))
        for field in ("schema_version", "guide_id", "head_commit", "source_fingerprint", "index_fingerprint", "tools"):
            if field not in payload:
                raise AssertionError(f"prepared marker missing {field}")
        marker_snapshot = snapshot(marker)

        sentinel = fixture / "sentinel"
        sentinel.write_text("do not overwrite\n", encoding="utf-8")
        sentinel.chmod(0o640)
        sentinel_snapshot = snapshot(sentinel)
        saved = fixture / "marker.saved"
        shutil.copy2(marker, saved)
        marker.unlink()
        marker.symlink_to(sentinel)
        require_failure(invoke(repository), "prepared marker는 일반 파일")
        if snapshot(sentinel) != sentinel_snapshot:
            raise AssertionError("prepare followed final marker symlink")
        marker.unlink()
        shutil.copy2(saved, marker)

        state_dir = repository / ".guide/data-engineering"
        state_saved = fixture / "state.saved"
        state_dir.rename(state_saved)
        escape = fixture / "state.escape"
        escape.mkdir()
        escape_sentinel = escape / "prepared.json"
        escape_sentinel.write_text("state sentinel\n", encoding="utf-8")
        state_dir.symlink_to(escape, target_is_directory=True)
        require_failure(invoke(repository), "symlink")
        if escape_sentinel.read_text(encoding="utf-8") != "state sentinel\n":
            raise AssertionError("prepare followed state-directory symlink")
        state_dir.unlink()
        state_saved.rename(state_dir)

        ready = fixture / "hold.ready"
        release = fixture / "hold.release"
        environment = os.environ.copy()
        environment.update(
            {
                "GUIDE_PREPARE_TEST_HOLD": "1",
                "GUIDE_PREPARE_TEST_READY_FILE": str(ready),
                "GUIDE_PREPARE_TEST_RELEASE_FILE": str(release),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        process = subprocess.Popen(
            ["bash", "prepare.sh"],
            cwd=repository,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + 10
        while not ready.is_file() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if not ready.is_file():
            process.terminate()
            output = process.communicate(timeout=5)[0]
            raise AssertionError(f"prepare hold fixture did not start\n{output}")
        process.send_signal(signal.SIGTERM)
        output = process.communicate(timeout=10)[0]
        if process.returncode == 0 or "PREPARE RESULT: FAIL" not in output:
            raise AssertionError(f"interrupted prepare reported success\n{output}")
        if snapshot(marker) != marker_snapshot:
            raise AssertionError("interrupted prepare changed previous marker")
        if list(state_dir.glob(".prepared.*")):
            raise AssertionError("interrupted prepare left owned marker temporary")

        if fingerprint(repository, "source") != source_before:
            raise AssertionError("prepare safety suite changed source bytes/modes")
        if fingerprint(repository, "workspace") != workspace_before:
            raise AssertionError("prepare safety suite changed learner workspace")
        if index_fingerprint(repository) != index_before:
            raise AssertionError("prepare safety suite changed Git index")

    print("PREPARE SAFETY: PASS (0600 atomic marker, symlink refusal, signal cleanup, state preserved)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
