#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/exercises/08-mica-capstone/skeleton"
TARGET=${1:-"$ROOT/.workspaces/mica"}

case "$TARGET" in
  /*) ;;
  *) TARGET="$PWD/$TARGET" ;;
esac

if [ -e "$TARGET" ]; then
  echo "workspace target already exists: $TARGET" >&2
  exit 1
fi

mkdir -p "$(dirname -- "$TARGET")"
cp -R "$SOURCE" "$TARGET"
find "$TARGET" -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
printf 'CREATED %s\n' "$TARGET"
printf 'NEXT PYTHONPATH=%s/src python3 -m mica check %s/exercises/08-mica-capstone/fixtures/valid/literal-main.mica --json\n' "$TARGET" "$ROOT"
