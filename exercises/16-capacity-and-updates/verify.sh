#!/bin/sh
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
mode=${1:-reference}
PYTHON=${PYTHON:-python3}
case "$mode" in
    skeleton|reference) ;;
    *) echo "사용법: $0 [skeleton|reference]" >&2; exit 2 ;;
esac

exec "$PYTHON" -B "$root/verify.py" "$mode"
