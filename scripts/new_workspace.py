#!/usr/bin/env python3
"""Create an isolated learner workspace without touching tracked source."""
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISES = (
    "01-time-step-analysis",
    "02-input-command-contract",
    "03-world-lifecycle-review",
    "04-asset-loading-plan",
    "05-save-and-replay-migration",
    "06-authority-and-latency",
    "07-performance-budget-review",
    "08-release-readiness",
)


def copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        return
    shutil.copytree(source, destination, symlinks=True)


def resolve_new_destination(raw: str) -> Path:
    requested = Path(raw).expanduser()
    if not requested.is_absolute():
        raise ValueError("workspace destination must be an absolute path")
    if requested.exists() or requested.is_symlink():
        raise ValueError("workspace destination must not already exist")

    parent = requested.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError("workspace parent must be a directory")
    destination = parent / requested.name
    root = ROOT.resolve()
    if destination == root or root in destination.parents or destination in root.parents:
        raise ValueError("workspace destination must be outside the guide repository")
    return destination


def create_workspace(destination: Path) -> None:
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent))
    try:
        exercises_root = staging / "exercises"
        exercises_root.mkdir()
        for exercise in EXERCISES:
            source = ROOT / "exercises" / exercise
            target = exercises_root / exercise
            target.mkdir()
            copy_tree(source / "inputs", target / "inputs")
            copy_tree(source / "template", target / "submission")

        project_source = ROOT / "projects" / "relay-arena-vertical-slice"
        project_target = staging / "relay-arena-vertical-slice"
        project_target.mkdir()
        copy_tree(project_source / "inputs", project_target / "inputs")
        copy_tree(project_source / "template", project_target / "submission")
        copy_tree(project_source / "starter", project_target / "starter")

        (staging / "README.md").write_text(
            "# game-development learner workspace\n\n"
            "This directory was created outside the guide repository. "
            "Edit only the copied `submission/` and `starter/` files.\n\n"
            "Run repository checkers by passing this workspace path explicitly; "
            "the guide never deletes or replaces this directory.\n",
            encoding="utf-8",
        )
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an isolated game-development workspace")
    parser.add_argument("destination")
    args = parser.parse_args()
    try:
        destination = resolve_new_destination(args.destination)
        create_workspace(destination)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"WORKSPACE_CREATED {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
