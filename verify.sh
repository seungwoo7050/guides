#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: Python 3 is required." >&2
  exit 1
}
command -v git >/dev/null 2>&1 || {
  echo "ERROR: Git is required." >&2
  exit 1
}
command -v make >/dev/null 2>&1 || {
  echo "ERROR: make is required." >&2
  exit 1
}

PYTHONDONTWRITEBYTECODE=1 python3 -B -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else "Python 3.12 or newer is required")'

PYTHONDONTWRITEBYTECODE=1 python3 -B - "$ROOT" "${VERIFY_LOG:-}" <<'PY'
from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any


root = Path(sys.argv[1]).resolve(strict=True)
requested_log = sys.argv[2]
marker_path = root / ".guide" / "agentic-systems" / "prepared.json"
targets = ("check", "test-reference", "test-starter-contract", "test-mutants", "test-capstone")


def make_log_path() -> Path:
    if not requested_log:
        descriptor, value = tempfile.mkstemp(prefix="agentic-systems-verify-", suffix=".log")
        os.close(descriptor)
        return Path(value).resolve()
    candidate = Path(requested_log)
    if not candidate.is_absolute():
        raise RuntimeError("VERIFY_LOG must be an absolute path outside the repository")
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        pass
    else:
        raise RuntimeError("VERIFY_LOG must stay outside the repository")
    if os.path.lexists(candidate):
        raise RuntimeError(f"VERIFY_LOG already exists; refusing to overwrite it: {candidate}")
    if not candidate.parent.is_dir():
        raise RuntimeError(f"VERIFY_LOG parent does not exist: {candidate.parent}")
    descriptor = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    return candidate


log_path = make_log_path()


def emit(message: str = "", *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    print(message, file=stream, flush=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def load_fingerprints():
    module_path = root / "scripts" / "source_fingerprint.py"
    spec = importlib.util.spec_from_file_location("source_fingerprint", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source fingerprint module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_marker() -> dict[str, Any]:
    if not os.path.lexists(marker_path):
        raise RuntimeError("preparation marker is missing; run ./prepare.sh first")
    metadata = marker_path.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(f"preparation marker is unsafe: {marker_path}")
    try:
        value = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read preparation marker: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("preparation marker root must be an object")
    return value


def marker_fingerprint_check(fingerprints) -> tuple[dict[str, Any], dict[str, Any]]:
    """The first substantive check: no build/test command runs before this."""

    marker = read_marker()
    expected_identity = {
        "marker_schema_version": "2",
        "guide": {"id": "agentic-systems", "version": "1.0"},
        "profile": {"id": "local-coding-agent", "version": "1.0"},
    }
    for field, expected in expected_identity.items():
        if marker.get(field) != expected:
            raise RuntimeError(f"marker {field} mismatch: expected={expected!r} actual={marker.get(field)!r}")
    contracts = marker.get("contracts")
    if not isinstance(contracts, dict) or contracts.get("action") != "1.0" or contracts.get("model_event") != "1.0":
        raise RuntimeError("marker contract versions are incompatible")

    current_source = fingerprints.fingerprint_report(root)
    marker_source = marker.get("source")
    for field in ("manifest_version", "exclusion_policy", "sha256", "count", "bytes", "manifest"):
        if not isinstance(marker_source, dict) or marker_source.get(field) != current_source.get(field):
            raise RuntimeError(f"prepared source {field} no longer matches the worktree")

    current_git = fingerprints.git_state(root)
    marker_git = marker.get("git")
    for field in ("head", "head_tree", "branch", "index_sha256", "index_bytes", "index_tree"):
        if not isinstance(marker_git, dict) or marker_git.get(field) != current_git.get(field):
            raise RuntimeError(f"prepared Git {field} no longer matches the repository")

    current_tools = {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": str(Path(sys.executable).resolve()),
        },
        "git": {
            "version": subprocess.run(
                ["git", "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            ).stdout.strip()
        },
    }
    if marker.get("tools") != current_tools:
        raise RuntimeError("prepared Python/Git tool identity no longer matches")
    current_platform = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_platform": platform.platform(),
    }
    if marker.get("platform") != current_platform:
        raise RuntimeError("prepared platform identity no longer matches")
    return current_source, current_git


def learner_workspace_state(fingerprints) -> dict[str, Any]:
    workspace = root / ".workspace"
    if not os.path.lexists(workspace):
        return {"exists": False}
    metadata = workspace.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(".workspace must be a real directory when present")
    directories: list[dict[str, str]] = []
    for current_raw, names, _files in os.walk(workspace, topdown=True, followlinks=False):
        current = Path(current_raw)
        for name in sorted(names):
            path = current / name
            child = path.lstat()
            if stat.S_ISDIR(child.st_mode) and not stat.S_ISLNK(child.st_mode):
                directories.append(
                    {
                        "path": path.relative_to(workspace).as_posix(),
                        "mode": f"{stat.S_IMODE(child.st_mode):04o}",
                    }
                )
    directories.sort(key=lambda item: item["path"])
    return {
        "exists": True,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "tree": fingerprints.fingerprint_report(workspace, apply_exclusions=False),
        "directories": directories,
    }


def create_isolated_copy(source: dict[str, Any]) -> Path:
    temporary = Path(tempfile.mkdtemp(prefix="agentic-systems-verify-"))
    isolated = temporary / "repository"
    isolated.mkdir(mode=0o700)
    for entry in source["manifest"]:
        relative = entry["path"]
        origin = root / relative
        destination = isolated / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if entry["type"] == "file":
            shutil.copy2(origin, destination, follow_symlinks=False)
        elif entry["type"] == "symlink":
            target = os.readlink(origin)
            if os.path.isabs(target):
                raise RuntimeError(
                    f"source symlink must stay relative in the isolated copy: {relative} -> {target}"
                )
            resolved = (origin.parent / target).resolve(strict=False)
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise RuntimeError(f"source symlink escapes the repository: {relative} -> {target}") from exc
            os.symlink(target, destination)
        else:
            raise RuntimeError(f"unknown manifest entry type: {entry['type']}")
    return isolated


def initialize_isolated_git(isolated: Path) -> None:
    commands = (
        ("git", "init", "--quiet"),
        ("git", "config", "user.name", "Guide Verifier"),
        ("git", "config", "user.email", "verifier.invalid@example.invalid"),
        ("git", "add", "-A"),
        ("git", "commit", "--quiet", "-m", "isolated verification snapshot"),
    )
    for command in commands:
        completed = subprocess.run(command, cwd=isolated, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
        if completed.stdout:
            for line in completed.stdout.rstrip().splitlines():
                emit(f"[isolation] {line}")
        if completed.returncode != 0:
            raise RuntimeError(f"isolated Git setup failed ({' '.join(command)}): exit={completed.returncode}")


def run_target(isolated: Path, target: str) -> bool:
    emit(f"=== make {target} ===")
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "TMPDIR": tempfile.gettempdir(),
    }
    completed = subprocess.run(
        ["make", target],
        cwd=isolated,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.stdout:
        for line in completed.stdout.rstrip().splitlines():
            emit(line)
    label = "PASS" if completed.returncode == 0 else "FAIL"
    emit(f"TARGET {target} {label} exit={completed.returncode}")
    return completed.returncode == 0


isolated: Path | None = None
status = 1
try:
    fingerprints = load_fingerprints()
    source_before, git_before = marker_fingerprint_check(fingerprints)
    emit(
        f"MARKER OK source={source_before['sha256']} entries={source_before['count']} "
        f"index_tree={git_before['index_tree']}"
    )

    workspace_before = learner_workspace_state(fingerprints)
    isolated = create_isolated_copy(source_before)
    initialize_isolated_git(isolated)
    isolated_before = fingerprints.fingerprint_report(isolated)
    if isolated_before["sha256"] != source_before["sha256"] or isolated_before["manifest"] != source_before["manifest"]:
        raise RuntimeError("isolated source copy does not match the prepared manifest")

    results = {target: run_target(isolated, target) for target in targets}

    isolated_after = fingerprints.fingerprint_report(isolated)
    if isolated_after != isolated_before:
        raise RuntimeError("verification changed source files in the isolated copy")
    source_after = fingerprints.fingerprint_report(root)
    git_after = fingerprints.git_state(root)
    workspace_after = learner_workspace_state(fingerprints)
    if source_after != source_before:
        raise RuntimeError("verification observed a change to the original source tree")
    if git_after != git_before:
        raise RuntimeError("verification observed a change to the original Git HEAD/index/tree")
    if workspace_after != workspace_before:
        raise RuntimeError("verification changed the learner .workspace tree")

    passed = sum(1 for value in results.values() if value)
    failed = len(results) - passed
    emit(f"SUMMARY passed={passed} failed={failed} skipped=0")
    if failed:
        raise RuntimeError("one or more mandatory verification targets failed")
    emit("RESULT VERIFY OK")
    status = 0
except Exception as exc:
    emit(f"RESULT VERIFY FAILED: {exc}", error=True)
    with log_path.open("a", encoding="utf-8") as handle:
        traceback.print_exc(file=handle)
finally:
    if isolated is not None:
        shutil.rmtree(isolated.parent, ignore_errors=True)
    emit(f"VERIFY LOG {log_path}")

raise SystemExit(status)
PY
