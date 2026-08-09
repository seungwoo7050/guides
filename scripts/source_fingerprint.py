#!/usr/bin/env python3
"""Deterministically fingerprint guide sources without following symlinks.

The source policy deliberately excludes learner workspaces and verification
artifacts.  The policy itself is versioned and included in every digest so a
future exclusion change invalidates an old preparation marker.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_VERSION = "2"
EXCLUSION_POLICY_VERSION = "agentic-systems-source-v2"

# These paths are outputs, local work, dependency trees, or tool caches.  They
# must never make a preparation fingerprint depend on a previous verification.
EXCLUDED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".guide",
        ".workspace",
        ".agent-state",
        ".verifier",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        ".venv",
        "venv",
        "node_modules",
        "htmlcov",
        "build",
        "dist",
        "target",
    }
)
EXCLUDED_FILE_NAMES = frozenset(
    {".git", ".guide", ".workspace", ".agent-state", ".verifier", ".DS_Store", ".coverage", "coverage.xml"}
)
EXCLUDED_FILE_SUFFIXES = (".pyc", ".pyo", ".log", ".tmp", ".swp")
EXCLUDED_FILE_PREFIXES = (".coverage.",)


class FingerprintError(RuntimeError):
    """Raised when a tree cannot be represented safely."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(128 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _excluded_file(name: str) -> bool:
    return (
        name in EXCLUDED_FILE_NAMES
        or name.startswith(EXCLUDED_FILE_PREFIXES)
        or name.endswith(EXCLUDED_FILE_SUFFIXES)
    )


def exclusion_policy() -> dict[str, Any]:
    return {
        "version": EXCLUSION_POLICY_VERSION,
        "directory_names": sorted(EXCLUDED_DIRECTORY_NAMES),
        "file_names": sorted(EXCLUDED_FILE_NAMES),
        "file_prefixes": list(EXCLUDED_FILE_PREFIXES),
        "file_suffixes": list(EXCLUDED_FILE_SUFFIXES),
    }


def tree_manifest(root: Path = ROOT, *, apply_exclusions: bool = True) -> list[dict[str, Any]]:
    """Return path, byte, mode, and symlink evidence for a directory tree."""

    root = root.resolve(strict=True)
    if not root.is_dir():
        raise FingerprintError(f"fingerprint root is not a directory: {root}")

    entries: list[dict[str, Any]] = []
    for current_raw, directories, files in os.walk(root, topdown=True, followlinks=False):
        current = Path(current_raw)

        kept_directories: list[str] = []
        for name in sorted(directories):
            path = current / name
            if apply_exclusions and name in EXCLUDED_DIRECTORY_NAMES:
                continue
            metadata = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                target = os.readlink(path)
                target_bytes = os.fsencode(target)
                entries.append(
                    {
                        "path": relative,
                        "type": "symlink",
                        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                        "bytes": len(target_bytes),
                        "target": target,
                        "sha256": _sha256_bytes(target_bytes),
                    }
                )
            elif stat.S_ISDIR(metadata.st_mode):
                kept_directories.append(name)
            else:
                raise FingerprintError(f"special directory entry is not supported: {relative}")
        directories[:] = kept_directories

        for name in sorted(files):
            if apply_exclusions and _excluded_file(name):
                continue
            path = current / name
            metadata = path.lstat()
            relative = path.relative_to(root).as_posix()
            if stat.S_ISLNK(metadata.st_mode):
                target = os.readlink(path)
                target_bytes = os.fsencode(target)
                entries.append(
                    {
                        "path": relative,
                        "type": "symlink",
                        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                        "bytes": len(target_bytes),
                        "target": target,
                        "sha256": _sha256_bytes(target_bytes),
                    }
                )
            elif stat.S_ISREG(metadata.st_mode):
                entries.append(
                    {
                        "path": relative,
                        "type": "file",
                        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                        "bytes": metadata.st_size,
                        "sha256": _file_sha256(path),
                    }
                )
            else:
                raise FingerprintError(f"special file is not supported: {relative}")

    entries.sort(key=lambda item: (item["path"], item["type"]))
    return entries


def manifest_digest(entries: Iterable[dict[str, Any]], *, apply_exclusions: bool = True) -> str:
    body = {
        "manifest_version": MANIFEST_VERSION,
        "exclusion_policy": exclusion_policy() if apply_exclusions else None,
        "entries": list(entries),
    }
    encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _sha256_bytes(encoded)


def fingerprint_report(root: Path = ROOT, *, apply_exclusions: bool = True) -> dict[str, Any]:
    entries = tree_manifest(root, apply_exclusions=apply_exclusions)
    return {
        "manifest_version": MANIFEST_VERSION,
        "exclusion_policy": exclusion_policy() if apply_exclusions else None,
        "sha256": manifest_digest(entries, apply_exclusions=apply_exclusions),
        "count": len(entries),
        "bytes": sum(int(entry["bytes"]) for entry in entries),
        "manifest": entries,
    }


def fingerprint() -> tuple[str, int]:
    """Compatibility helper used by older preparation scripts."""

    report = fingerprint_report(ROOT)
    return str(report["sha256"]), int(report["count"])


def _git(root: Path, *arguments: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise FingerprintError(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def git_state(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    top = Path(_git(root, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top != root:
        raise FingerprintError(f"expected Git root {root}, got {top}")

    index_raw = _git(root, "rev-parse", "--git-path", "index")
    index_path = Path(index_raw)
    if not index_path.is_absolute():
        index_path = root / index_path
    index_bytes = index_path.read_bytes() if index_path.is_file() else b""

    head = _git(root, "rev-parse", "--verify", "HEAD", check=False) or None
    head_tree = _git(root, "rev-parse", "--verify", "HEAD^{tree}", check=False) or None
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False) or None
    return {
        "head": head,
        "head_tree": head_tree,
        "branch": branch,
        "index_sha256": _sha256_bytes(index_bytes),
        "index_bytes": len(index_bytes),
        "index_tree": _git(root, "write-tree"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--all", action="store_true", help="include cache/output names normally excluded")
    parser.add_argument("--json", action="store_true", help="emit the full manifest as JSON")
    parser.add_argument("--git", action="store_true", help="include Git HEAD/index/tree evidence")
    args = parser.parse_args()

    try:
        report = fingerprint_report(args.root, apply_exclusions=not args.all)
        if args.git:
            report["git"] = git_state(args.root)
    except (FingerprintError, OSError) as exc:
        print(f"fingerprint error: {exc}", file=os.sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{report['sha256']} {report['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
