#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "PREPARE ERROR: Python 3가 필요합니다." >&2
  exit 1
fi
exec python3 "$ROOT/scripts/prepare.py"
