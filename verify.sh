#!/usr/bin/env sh
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT" || exit 1

MARKER=.guide/cybersecurity/prepared.json
if [ -L "$MARKER" ] || [ ! -f "$MARKER" ]; then
  echo "먼저 ./prepare.sh를 실행하십시오. 일반 파일 marker가 필요합니다." >&2
  exit 1
fi

WORK_MODE=${CYBERSECURITY_VERIFY_WORK:-0}
case "$WORK_MODE" in
  0|1) ;;
  *)
    echo "CYBERSECURITY_VERIFY_WORK는 0 또는 1이어야 합니다." >&2
    exit 1
    ;;
esac

if [ "${VERIFY_LOG:-}" = "" ]; then
  VERIFY_LOG=$(mktemp /tmp/guide-cybersecurity-verify.XXXXXX) || {
    echo "검증 log를 만들 수 없습니다." >&2
    exit 1
  }
else
  python3 - "$ROOT" "$VERIFY_LOG" <<'PY'
from __future__ import annotations

import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2])
if not target.is_absolute():
    raise SystemExit("VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다.")
if os.path.lexists(target):
    raise SystemExit("VERIFY_LOG는 기존 파일이나 symlink를 덮어쓸 수 없습니다.")

parent = target.parent
if not parent.exists() or not parent.is_dir():
    raise SystemExit("VERIFY_LOG의 상위 디렉터리는 이미 존재하는 일반 디렉터리여야 합니다.")

resolved = parent.resolve(strict=True) / target.name
if resolved == root or root in resolved.parents:
    raise SystemExit("VERIFY_LOG는 저장소 내부에 둘 수 없습니다.")

flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
descriptor = os.open(target, flags, 0o600)
os.close(descriptor)
PY
  log_status=$?
  if [ "$log_status" -ne 0 ]; then
    exit "$log_status"
  fi
fi

overall_status=0
check_count=0
pass_count=0
fail_count=0
skip_count=0

run_check() {
  check_label=$1
  shift
  check_count=$((check_count + 1))
  printf '[RUN] %s\n' "$check_label" >>"$VERIFY_LOG"
  "$@" >>"$VERIFY_LOG" 2>&1
  check_status=$?
  if [ "$check_status" -eq 0 ]; then
    pass_count=$((pass_count + 1))
    printf '[PASS] %s\n' "$check_label" >>"$VERIFY_LOG"
  else
    fail_count=$((fail_count + 1))
    overall_status=1
    printf '[FAIL] %s exit=%s\n' "$check_label" "$check_status" >>"$VERIFY_LOG"
  fi
}

run_check "prepared-source-fingerprint" \
  python3 scripts/source_fingerprint.py --check-marker "$MARKER"
run_check "repository-reference-meta" \
  python3 scripts/verify_repository.py

if [ "$WORK_MODE" -eq 1 ]; then
  run_check "exercise-workspaces" \
    python3 scripts/verify_repository.py --workspaces-only
  run_check "capstone-work" \
    python3 scripts/verify_capstone.py projects/synthetic-service-security-review/work
else
  skip_count=$((skip_count + 1))
  printf '%s\n' \
    '[SKIP] learner-work: CYBERSECURITY_VERIFY_WORK=1일 때만 학습자 제출물을 검사합니다.' \
    >>"$VERIFY_LOG"
fi

printf '[SUMMARY] checks=%s pass=%s fail=%s skip=%s\n' \
  "$check_count" "$pass_count" "$fail_count" "$skip_count" >>"$VERIFY_LOG"

cat "$VERIFY_LOG"
cat_status=$?
if [ "$cat_status" -ne 0 ]; then
  echo "검증 log를 읽을 수 없습니다: $VERIFY_LOG" >&2
  overall_status=1
fi
echo "VERIFY LOG $VERIFY_LOG"
exit "$overall_status"
