#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"

if [ ! -f .guide/distributed-systems/prepared.json ]; then
  echo '먼저 make prepare 또는 ./prepare.sh를 실행하십시오.' >&2
  exit 1
fi

LOG=${VERIFY_LOG:-"/tmp/guide-distributed-systems-verify-$$.log"}
case "$LOG" in
  /*) ;;
  *) echo 'VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다.' >&2; exit 1 ;;
esac
case "$LOG" in
  "$ROOT"|"$ROOT"/*) echo 'VERIFY_LOG는 저장소 내부일 수 없습니다.' >&2; exit 1 ;;
esac

mkdir -p "$(dirname -- "$LOG")"
if python3 scripts/verify.py >"$LOG" 2>&1; then
  cat "$LOG"
  printf 'VERIFY_LOG %s\n' "$LOG"
else
  status=$?
  cat "$LOG" >&2
  exit "$status"
fi
