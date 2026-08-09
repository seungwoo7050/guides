#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, timeout: float = 10) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False, timeout=timeout)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="language-infrastructure-") as temporary:
        external = Path(temporary) / "mica"
        created = run(sys.executable, "scripts/new_workspace.py", str(external))
        require(created.returncode == 0 and (external / "pyproject.toml").is_file(), created.stderr)
        duplicate = run(sys.executable, "scripts/new_workspace.py", str(external))
        require(duplicate.returncode != 0, "existing workspace was overwritten")
        require((external / "pyproject.toml").is_file(), "duplicate attempt damaged workspace")
        refused = run(sys.executable, "scripts/purge_workspace.py", str(external))
        require(refused.returncode != 0 and external.is_dir(), "external workspace purge was not refused")

        symlink = Path(temporary) / "workspace-link"
        symlink.symlink_to(external, target_is_directory=True)
        linked = run(sys.executable, "scripts/new_workspace.py", str(symlink))
        require(linked.returncode != 0, "symlink workspace target was accepted")

    in_repo = ROOT / ".workspaces" / f"infrastructure-{os.getpid()}"
    try:
        created = run(sys.executable, "scripts/new_workspace.py", str(in_repo))
        require(created.returncode == 0, created.stderr)
        cleaned = run(sys.executable, "scripts/clean_generated.py")
        require(cleaned.returncode == 0 and in_repo.is_dir(), "default clean removed learner workspace")
        purged = run(sys.executable, "scripts/purge_workspace.py", str(in_repo))
        require(purged.returncode == 0 and not in_repo.exists(), purged.stderr)
    finally:
        shutil.rmtree(in_repo, ignore_errors=True)

    started = time.monotonic()
    timed = run(
        sys.executable,
        "scripts/run_with_timeout.py",
        "0.2",
        "--",
        sys.executable,
        "-c",
        "import time; time.sleep(30)",
        timeout=5,
    )
    elapsed = time.monotonic() - started
    require(timed.returncode == 124 and elapsed < 3, f"timeout contract failed: {timed.returncode}, {elapsed}")
    print("PASS infrastructure workspace-preservation no-overwrite purge-boundary timeout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
