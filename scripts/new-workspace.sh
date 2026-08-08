#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

[[ $# -eq 1 ]] || {
  printf '사용법: ./scripts/new-workspace.sh EXERCISE_SLUG\n' >&2
  exit 2
}
[[ "$(pwd -P)" == "$ROOT_DIR" ]] || {
  printf '저장소 루트에서 실행해야 합니다.\n' >&2
  exit 2
}

exec python3 "$ROOT_DIR/scripts/workspace.py" create "$1"
