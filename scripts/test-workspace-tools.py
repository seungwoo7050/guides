#!/usr/bin/env python3
"""Exercise workspace creation against traversal and symlink mutants."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALID_EXERCISE = "exercises/02-storage-and-indexes/01-slotted-page"


def copy_source(destination: Path) -> None:
    shutil.copytree(
        ROOT,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(".git", ".guide", ".verify", "workspace", "__pycache__", "*.pyc", "*.pyo"),
    )


def run(root: Path, script: str, argument: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(root / "scripts" / script), argument],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-db-workspace-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        created = run(root, "new-workspace.sh", VALID_EXERCISE)
        if created.returncode != 0:
            raise AssertionError(created.stdout + created.stderr)
        checked = run(root, "check-workspace.sh", VALID_EXERCISE)
        initial_output = checked.stdout + checked.stderr
        if checked.returncode == 0 or "GUIDE_SEMANTIC:slotted-page-insert" not in initial_output:
            raise AssertionError(checked.stdout + checked.stderr)
        workspace = root / VALID_EXERCISE / "workspace"
        reference = root / VALID_EXERCISE / "reference"
        for source in reference.iterdir():
            if source.is_file():
                shutil.copy2(source, workspace / source.name)
        completed = run(root, "check-workspace.sh", VALID_EXERCISE)
        if completed.returncode != 0 or "[PASS] learner workspace" not in completed.stdout:
            raise AssertionError(completed.stdout + completed.stderr)
        traversal = run(root, "new-workspace.sh", "exercises/../docs")
        if traversal.returncode == 0 or "manifest에 없는" not in traversal.stderr:
            raise AssertionError("path traversal mutant was not rejected")
        print("[PASS] workspace: designated start failure, completed PASS, traversal rejection")

    with tempfile.TemporaryDirectory(prefix="guide-db-workspace-symlink-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        dangling = root / VALID_EXERCISE / "skeleton/dangling"
        dangling.symlink_to("missing-target")
        result = run(root, "new-workspace.sh", VALID_EXERCISE)
        if result.returncode == 0 or "symlink" not in result.stderr:
            raise AssertionError("dangling skeleton symlink mutant was not rejected")
        print("[PASS] workspace: dangling symlink rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
