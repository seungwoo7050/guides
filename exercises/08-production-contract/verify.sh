#!/bin/sh
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
mode=${1:-workspace}
PYTHON=${PYTHON:-python3}
case "$mode" in
    skeleton|workspace|reference) ;;
    *) echo "사용법: $0 [skeleton|workspace|reference]" >&2; exit 2 ;;
esac
[ -d "$root/$mode" ] || { echo "구현 디렉터리가 없습니다: $root/$mode" >&2; exit 2; }
[ ! -L "$root/$mode" ] || { echo "구현 디렉터리 symlink를 허용하지 않습니다." >&2; exit 2; }
if find "$root/$mode" -type l -print -quit | grep -q .
then
    echo "구현 디렉터리 내부 symlink를 허용하지 않습니다." >&2
    exit 2
fi

exec "$PYTHON" -B "$root/verify.py" "$root/$mode/contract.yaml"
