#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
TARGET=${1:-"$ROOT/.workspace/replicated-kv"}

case "$TARGET" in
  /*) ;;
  *) TARGET="$ROOT/$TARGET" ;;
esac

if [ -e "$TARGET" ]; then
  echo "대상이 이미 존재합니다: $TARGET" >&2
  exit 1
fi

mkdir -p "$(dirname -- "$TARGET")"
cp -R "$ROOT/capstone/starter" "$TARGET"
printf 'CREATED %s\n' "$TARGET"
printf 'RUN CAPSTONE_ROOT=%s python3 -m unittest discover -s capstone/tests -v\n' "$TARGET"
