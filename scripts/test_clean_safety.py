#!/usr/bin/env python3
"""Prove cleanup removes only guide-owned state and preserves learner bytes/modes."""

from __future__ import annotations

import tempfile
from pathlib import Path

from clean_generated import clean_tree
from repository_state import fingerprint


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-data-clean-") as temporary:
        root = Path(temporary) / "repository"
        workspace = root / "exercises/topic/workspace"
        (workspace / "learner/__pycache__").mkdir(parents=True)
        (workspace / ".guide").mkdir()
        (root / "scripts/__pycache__").mkdir(parents=True)
        (root / ".guide/data-engineering").mkdir(parents=True)
        (root / "docs/workspace/__pycache__").mkdir(parents=True)
        learner = workspace / "learner/answer.pyc"
        learner.write_text("learner byte-named data\n", encoding="utf-8")
        learner.chmod(0o640)
        (workspace / "learner/__pycache__/answer.pyc").write_text("learner cache data\n", encoding="utf-8")
        (workspace / ".guide/sentinel").write_text("learner hidden state\n", encoding="utf-8")
        (root / "scripts/__pycache__/tool.pyc").write_text("generated\n", encoding="utf-8")
        (root / ".guide/data-engineering/prepared.json").write_text("generated\n", encoding="utf-8")
        (root / "docs/workspace/__pycache__/source.pyc").write_text("generated\n", encoding="utf-8")
        workspace_before = fingerprint(root, "workspace")
        clean_tree(root)
        if fingerprint(root, "workspace") != workspace_before:
            raise AssertionError("cleanup changed learner workspace bytes or modes")
        if (root / ".guide").exists() or (root / "scripts/__pycache__").exists():
            raise AssertionError("cleanup left guide-owned generated state")
        if (root / "docs/workspace/__pycache__").exists():
            raise AssertionError("docs/workspace was mistaken for learner workspace")

        external = Path(temporary) / "external"
        external.mkdir()
        sentinel = external / "sentinel"
        sentinel.write_text("preserve\n", encoding="utf-8")
        (root / ".guide").symlink_to(external, target_is_directory=True)
        clean_tree(root)
        if (root / ".guide").exists() or not sentinel.is_file():
            raise AssertionError("cleanup followed a .guide symlink")

    print("CLEAN SAFETY: PASS (generated state removed; learner/symlink target preserved)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
