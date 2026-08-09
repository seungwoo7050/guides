#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ "$#" -ne 1 ]; then
    echo "사용법: scripts/new_workspace.sh exercises/NN-name 또는 projects/name" >&2
    exit 2
fi
TARGET=$1
case "$TARGET" in
    exercises/*|projects/*) ;;
    *) echo "허용된 경로는 exercises/ 또는 projects/ 아래입니다." >&2; exit 2 ;;
esac
SOURCE="$ROOT/$TARGET/template"
NAME=$(basename "$TARGET")
DEST="$ROOT/.workspace/$NAME"
[ -d "$SOURCE" ] || { echo "template이 없습니다: $SOURCE" >&2; exit 1; }
[ ! -e "$DEST" ] || { echo "workspace가 이미 있습니다: $DEST" >&2; exit 1; }
mkdir -p "$ROOT/.workspace"
cp -R "$SOURCE" "$DEST"
echo "$DEST"
