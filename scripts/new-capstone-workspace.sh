#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
cd "$ROOT"
PYTHONDONTWRITEBYTECODE=1 python3 scripts/new_capstone_workspace.py "$@"
