#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 1 ]; then
    echo "사용법: scripts/check_workspace.sh exercises/NN-name 또는 projects/name" >&2
    exit 2
fi
TARGET=$1
NAME=$(basename "$TARGET")
WORK="$ROOT/.workspace/$NAME"
CONTRACT="$ROOT/$TARGET/contract.json"
[ -d "$WORK" ] || { echo "workspace가 없습니다: $WORK" >&2; exit 1; }
[ -f "$CONTRACT" ] || { echo "contract가 없습니다: $CONTRACT" >&2; exit 1; }
python3 "$ROOT/scripts/check_artifact.py" "$WORK" "$CONTRACT"
