#!/usr/bin/env python3
"""Regression tests for source, workspace, mode, symlink, and index state."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from repository_state import fingerprint, index_fingerprint


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-data-state-") as temporary:
        root = Path(temporary) / "repository"
        (root / "docs/workspace").mkdir(parents=True)
        (root / "exercises/topic/workspace").mkdir(parents=True)
        (root / ".guide/data-engineering").mkdir(parents=True)
        source = root / "docs/workspace/source.md"
        learner = root / "exercises/topic/workspace/answer.py"
        ignored = root / ".guide/data-engineering/prepared.json"
        source.write_text("source one\n", encoding="utf-8")
        source.chmod(0o644)
        learner.write_text("learner one\n", encoding="utf-8")
        ignored.write_text("ignored one\n", encoding="utf-8")
        link = root / "link"
        link.symlink_to("docs/workspace/source.md")

        source_before = fingerprint(root, "source")
        workspace_before = fingerprint(root, "workspace")
        learner.write_text("learner two\n", encoding="utf-8")
        require(fingerprint(root, "source") == source_before, "learner workspace changed source state")
        require(fingerprint(root, "workspace") != workspace_before, "learner change was not detected")

        source.write_text("source two\n", encoding="utf-8")
        require(fingerprint(root, "source") != source_before, "docs/workspace was incorrectly ignored")
        source_before = fingerprint(root, "source")
        source.chmod(0o600)
        require(fingerprint(root, "source") != source_before, "regular-file mode change was not detected")

        source_before = fingerprint(root, "source")
        link.unlink()
        link.symlink_to("docs/workspace/missing.md")
        require(fingerprint(root, "source") != source_before, "symlink target change was not detected")
        source_before = fingerprint(root, "source")
        ignored.write_text("ignored two\n", encoding="utf-8")
        require(fingerprint(root, "source") == source_before, ".guide state affected source fingerprint")

        subprocess.run(["git", "init", "-q", str(root)], check=True)
        tracked = root / "tracked.txt"
        tracked.write_text("one\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
        index_before = index_fingerprint(root)
        tracked.write_text("two\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
        require(index_fingerprint(root) != index_before, "raw Git index change was not detected")

    print("REPOSITORY STATE: PASS (source/workspace/mode/symlink/index boundaries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
