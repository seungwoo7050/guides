#!/usr/bin/env python3
"""Verify workspace creation and cleanup never overwrite learner bytes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(root: Path, *command: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="guide-ds-workspace-cache-") as cache:
        environment["PYTHONPYCACHEPREFIX"] = cache
        return subprocess.run(
            list(command), cwd=root, env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
        )


def copy_repository(target: Path) -> Path:
    shutil.copytree(
        ROOT, target, symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git", ".guide", ".workspace", "__pycache__", "*.pyc", "*.pyo", "*.log"
        ),
    )
    return target


def assert_sentinel(path: Path, expected: str = "valuable\n") -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != expected:
        raise AssertionError(f"external sentinel changed: {path}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="guide-ds-workspace-test-") as temporary:
        base = Path(temporary)
        target = base / "learner/replicated-kv"
        created = run(ROOT, sys.executable, "scripts/new_capstone_workspace.py", str(target))
        if created.returncode != 0 or not (target / "dskv/node.py").is_file():
            raise AssertionError(f"workspace creation failed\n{created.stdout}\n{created.stderr}")
        sentinel = target / "learner-notes.txt"
        sentinel.write_text("preserve me\n", encoding="utf-8")
        repeated = run(ROOT, sys.executable, "scripts/new_capstone_workspace.py", str(target))
        if repeated.returncode == 0 or sentinel.read_text(encoding="utf-8") != "preserve me\n":
            raise AssertionError("existing workspace was overwritten")
        alias = base / "alias"
        os.symlink(target, alias)
        aliased = run(ROOT, sys.executable, "scripts/new_capstone_workspace.py", str(alias))
        if aliased.returncode == 0 or sentinel.read_text(encoding="utf-8") != "preserve me\n":
            raise AssertionError("symlink workspace alias was not rejected safely")

        external_parent = base / "external-workspace-parent"
        external_parent.mkdir()
        intermediate_alias = base / "intermediate-alias"
        os.symlink(external_parent, intermediate_alias)
        intermediate = run(
            ROOT, sys.executable, "scripts/new_capstone_workspace.py",
            str(intermediate_alias / "fresh"),
        )
        if intermediate.returncode == 0 or (external_parent / "fresh").exists():
            raise AssertionError("intermediate workspace symlink redirected creation")

        copy = copy_repository(base / "repository")
        learner = copy / ".workspace/notes"
        learner.mkdir(parents=True)
        learner_sentinel = learner / "keep.txt"
        learner_sentinel.write_text("keep\n", encoding="utf-8")
        generated = copy / ".guide/distributed-systems/cache.txt"
        generated.parent.mkdir(parents=True)
        generated.write_text("generated\n", encoding="utf-8")
        cleaned = run(copy, sys.executable, "scripts/clean_generated.py")
        if cleaned.returncode != 0 or not learner_sentinel.is_file() or generated.exists():
            raise AssertionError("clean did not preserve workspace or remove owned state")

        for action in ("prepare", "clean"):
            parent_copy = copy_repository(base / f"{action}-parent-symlink")
            parent_external = base / f"{action}-parent-external"
            parent_owned = parent_external / "distributed-systems"
            parent_owned.mkdir(parents=True)
            parent_sentinel = parent_owned / "valuable.txt"
            parent_sentinel.write_text("valuable\n", encoding="utf-8")
            os.symlink(parent_external, parent_copy / ".guide")
            parent_result = run(
                parent_copy, sys.executable,
                f"scripts/{'prepare.py' if action == 'prepare' else 'clean_generated.py'}",
            )
            if parent_result.returncode == 0:
                raise AssertionError(f"{action} accepted a .guide parent symlink")
            assert_sentinel(parent_sentinel)

            target_copy = copy_repository(base / f"{action}-target-symlink")
            guide = target_copy / ".guide"
            guide.mkdir()
            target_external = base / f"{action}-target-external"
            target_external.mkdir()
            target_sentinel = target_external / "valuable.txt"
            target_sentinel.write_text("valuable\n", encoding="utf-8")
            os.symlink(target_external, guide / "distributed-systems")
            target_result = run(
                target_copy, sys.executable,
                f"scripts/{'prepare.py' if action == 'prepare' else 'clean_generated.py'}",
            )
            if target_result.returncode == 0:
                raise AssertionError(f"{action} accepted a generated target symlink")
            assert_sentinel(target_sentinel)

    print(
        "WORKSPACE TOOLS OK create=1 existing-reject=1 final-symlink-reject=1 "
        "intermediate-symlink-reject=1 prepare-symlink-reject=2 "
        "clean-symlink-reject=2 clean-preserve=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
