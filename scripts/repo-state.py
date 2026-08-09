#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def load_fingerprint_module(root: Path) -> ModuleType:
    path = root / "scripts/source-fingerprint.py"
    spec = importlib.util.spec_from_file_location("guide_source_fingerprint", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_git(root: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *arguments])


def workspace_state(root: Path, fingerprint_module: ModuleType) -> dict[str, object]:
    workspaces: dict[str, object] = {}
    exercises = root / "exercises"
    if not exercises.exists():
        return workspaces
    for path in sorted(exercises.rglob("workspace")):
        if path.is_symlink():
            raise AssertionError(f"workspace symlink is not allowed: {path.relative_to(root)}")
        if not path.is_dir():
            continue
        digest, entries = fingerprint_module.fingerprint(path)
        workspaces[path.relative_to(root).as_posix()] = {
            "sha256": digest,
            "entries": entries,
        }
    return workspaces


def collect(root: Path) -> dict[str, object]:
    root = root.resolve()
    git_root = Path(run_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if git_root != root:
        raise AssertionError(f"guide root is not the Git root: {root} != {git_root}")
    fingerprint_module = load_fingerprint_module(root)
    source_sha, source_entries = fingerprint_module.fingerprint(root)
    index = run_git(root, "ls-files", "--stage", "-z")
    return {
        "head": run_git(root, "rev-parse", "--verify", "HEAD").decode().strip(),
        "index_sha256": hashlib.sha256(index).hexdigest(),
        "source_sha256": source_sha,
        "source_entries": source_entries,
        "workspaces": workspace_state(root, fingerprint_module),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        state = collect(args.root)
    except (AssertionError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    print(json.dumps(state, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
