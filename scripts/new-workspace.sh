#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ "$#" -ne 1 ]; then
  echo "usage: $0 /absolute/new/workspace" >&2
  exit 2
fi

exec python3 "$ROOT/scripts/new_workspace.py" "$1"
