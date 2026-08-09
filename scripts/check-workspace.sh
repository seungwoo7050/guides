#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 1 ]; then
  echo 'usage: ./scripts/check-workspace.sh exercises/<path>' >&2
  exit 2
fi
exec python3 -B "$ROOT/scripts/exercise_tool.py" check "$1" --source workspace
