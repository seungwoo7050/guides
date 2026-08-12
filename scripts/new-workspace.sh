#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

fail() {
  printf 'new-workspace: %s\n' "$*" >&2
  exit 1
}

[[ $# -eq 1 ]] || fail 'usage: scripts/new-workspace.sh SLUG'
SLUG="$1"

case "$SLUG" in
  uncertain-outcome)
    SOURCE="exercises/01-boundaries-and-failure/01-uncertain-outcome/skeleton"
    ;;
  service-boundary)
    SOURCE="exercises/01-boundaries-and-failure/02-service-boundary/skeleton"
    ;;
  request-decision)
    SOURCE="exercises/01-boundaries-and-failure/03-request-decision/skeleton"
    ;;
  duplicate-delivery)
    SOURCE="exercises/02-delivery-and-consistency/01-duplicate-delivery/skeleton"
    ;;
  outbox-reconciliation)
    SOURCE="exercises/02-delivery-and-consistency/02-outbox-reconciliation/skeleton"
    ;;
  contracts-and-order)
    SOURCE="exercises/02-delivery-and-consistency/03-contracts-and-order/skeleton"
    ;;
  read-model-rebuild)
    SOURCE="exercises/02-delivery-and-consistency/04-read-model-rebuild/skeleton"
    ;;
  retry-budget)
    SOURCE="exercises/03-resilience-and-load/01-retry-budget/skeleton"
    ;;
  backpressure)
    SOURCE="exercises/03-resilience-and-load/02-backpressure/skeleton"
    ;;
  release-manifest)
    SOURCE="exercises/04-release-and-evidence/01-release-manifest/skeleton"
    ;;
  observability-correlation)
    SOURCE="exercises/04-release-and-evidence/02-observability-correlation/skeleton"
    ;;
  chaos-evidence)
    SOURCE="exercises/04-release-and-evidence/03-chaos-evidence/skeleton"
    ;;
  performance-gate)
    SOURCE="exercises/04-release-and-evidence/04-performance-gate/skeleton"
    ;;
  reservation-flow)
    SOURCE="exercises/05-capstone/reservation-flow/skeleton"
    ;;
  *)
    fail "unknown exercise slug: $SLUG"
    ;;
esac

python3 - "$ROOT" "$SOURCE" "$SLUG" <<'PY'
from __future__ import annotations

import ctypes
import errno
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"new-workspace: {message}")


def require_plain_tree(path: Path) -> None:
    for candidate in (path, *path.rglob("*")):
        metadata = candidate.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            fail(f"canonical skeleton contains a symlink: {candidate}")


def publish_no_replace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    encoded_source = os.fsencode(source)
    encoded_destination = os.fsencode(destination)
    if sys.platform == "darwin":
        function = libc.renamex_np
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        status = function(encoded_source, encoded_destination, 0x00000004)
    elif sys.platform.startswith("linux"):
        function = libc.renameat2
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        status = function(-100, encoded_source, -100, encoded_destination, 0x00000001)
    else:
        fail(f"exclusive atomic publish is unsupported on {sys.platform}")
    if status:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            fail(f"workspace already exists: {destination}")
        raise OSError(error, os.strerror(error), destination)


root = Path(sys.argv[1]).resolve(strict=True)
source_relative = Path(sys.argv[2])
slug = sys.argv[3]
if not slug or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in slug):
    fail(f"invalid exercise slug: {slug}")

source = root / source_relative
try:
    resolved_source = source.resolve(strict=True)
except OSError as error:
    fail(f"cannot resolve canonical skeleton: {error}")
if resolved_source != source or not source.is_dir():
    fail(f"canonical skeleton is not a plain directory: {source_relative}")
require_plain_tree(source)

workspace = root / ".workspace"
try:
    workspace.mkdir(mode=0o700)
except FileExistsError:
    pass
try:
    workspace_state = workspace.lstat()
except OSError as error:
    fail(f"cannot inspect .workspace: {error}")
if not stat.S_ISDIR(workspace_state.st_mode) or workspace.is_symlink():
    fail(".workspace must be a real directory")
if workspace.resolve(strict=True) != workspace:
    fail(".workspace must not escape the repository")

destination = workspace / slug
if destination.exists() or destination.is_symlink():
    fail(f"workspace already exists: {destination}")

lock = workspace / f".{slug}.lock"
temporary: Path | None = None
try:
    lock.mkdir(mode=0o700)
except FileExistsError:
    fail(f"another workspace creation is active for {slug}")

try:
    if destination.exists() or destination.is_symlink():
        fail(f"workspace appeared while acquiring the lock: {destination}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{slug}.tmp.", dir=workspace))
    shutil.copytree(source, temporary, dirs_exist_ok=True, symlinks=False)
    require_plain_tree(temporary)
    publish_no_replace(temporary, destination)
    temporary = None
finally:
    if temporary is not None and temporary.is_dir() and not temporary.is_symlink():
        shutil.rmtree(temporary)
    try:
        lock.rmdir()
    except OSError:
        pass

print(f"workspace created: {destination}")
PY
