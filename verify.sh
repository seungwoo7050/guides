#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd -P)
MARKER="$ROOT/.guide/java/prepared.json"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEFAULT_LOG="/tmp/guide-java-verify-${TIMESTAMP}-$$.log"
REQUESTED_LOG=${VERIFY_LOG:-$DEFAULT_LOG}
FALLBACK_LOG="/tmp/guide-java-verify-preflight-${TIMESTAMP}-$$.log"
FINAL_LOG=
WORK_ROOT=
WORK_TREE=
ACTIVE_PID=
SOURCE_BEFORE=
PREPARATION_FINGERPRINT=
INDEX_BEFORE=
PASSED=0
FAILED=0
SKIPPED=0
CLEANED=0
STATE_CHECKED=0

canonical_path() {
  python3 - "$1" <<'PY'
import sys
from pathlib import Path

try:
    print(Path(sys.argv[1]).resolve(strict=False))
except (OSError, RuntimeError) as error:
    raise SystemExit(str(error))
PY
}

emit_preflight_failure() {
  local message=$1 fallback
  fallback=$(canonical_path "$FALLBACK_LOG" 2>/dev/null) || fallback="$FALLBACK_LOG"
  mkdir -p "$(dirname "$fallback")" 2>/dev/null || true
  {
    printf '[FAIL] %s\n' "$message"
    printf 'RESULT: FAIL\n'
    printf 'passed=0 failed=1 skipped=0\n'
    printf 'VERIFY LOG: %s\n' "$fallback"
  } | tee "$fallback" >&2
  exit 2
}

resolve_log() {
  local canonical_root canonical_log
  [[ "$REQUESTED_LOG" == /* ]] \
    || emit_preflight_failure "VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다: $REQUESTED_LOG"
  canonical_root=$(canonical_path "$ROOT") \
    || emit_preflight_failure "저장소 경로를 해석하지 못했습니다."
  canonical_log=$(canonical_path "$REQUESTED_LOG") \
    || emit_preflight_failure "VERIFY_LOG 경로를 해석하지 못했습니다: $REQUESTED_LOG"
  case "$canonical_log" in
    "$canonical_root"|"$canonical_root"/*)
      emit_preflight_failure "VERIFY_LOG는 저장소 밖이어야 합니다: $canonical_log"
      ;;
  esac
  FINAL_LOG=$canonical_log
  mkdir -p "$(dirname "$FINAL_LOG")" \
    || emit_preflight_failure "VERIFY_LOG parent를 만들 수 없습니다: $FINAL_LOG"
  : >"$FINAL_LOG" \
    || emit_preflight_failure "VERIFY_LOG를 쓸 수 없습니다: $FINAL_LOG"
}

resolve_log

say() {
  printf '%s\n' "$*" | tee -a "$FINAL_LOG"
}

child_pids() {
  pgrep -P "$1" 2>/dev/null || true
}

signal_tree() {
  local signal=$1 pid=$2 child
  while IFS= read -r child; do
    [[ -n "$child" ]] || continue
    signal_tree "$signal" "$child"
  done < <(child_pids "$pid")
  kill -"$signal" "$pid" 2>/dev/null || true
}

stop_active_tree() {
  local attempt
  [[ -n "${ACTIVE_PID:-}" ]] || return
  signal_tree TERM "$ACTIVE_PID"
  for attempt in 1 2 3 4; do
    kill -0 "$ACTIVE_PID" 2>/dev/null || break
    sleep 0.05
  done
  if kill -0 "$ACTIVE_PID" 2>/dev/null; then
    signal_tree KILL "$ACTIVE_PID"
  fi
  wait "$ACTIVE_PID" 2>/dev/null || true
  ACTIVE_PID=
}

cleanup() {
  [[ $CLEANED -eq 0 ]] || return
  CLEANED=1
  cd "$ROOT" 2>/dev/null || true
  [[ -z "${WORK_ROOT:-}" || ! -d "$WORK_ROOT" ]] || rm -rf "$WORK_ROOT"
}

check_original_state() {
  local source_after index_after
  [[ $STATE_CHECKED -eq 0 ]] || return
  STATE_CHECKED=1
  [[ -n "$SOURCE_BEFORE" && -n "$INDEX_BEFORE" ]] || return
  source_after=$(python3 "$ROOT/scripts/guide_state.py" capture "$ROOT" 2>>"$FINAL_LOG") \
    || { say "[FAIL] 검증 후 source 상태를 기록하지 못했습니다."; FAILED=$((FAILED + 1)); return; }
  index_after=$(python3 "$ROOT/scripts/guide_state.py" index-state "$ROOT" 2>>"$FINAL_LOG") \
    || { say "[FAIL] 검증 후 Git index 상태를 기록하지 못했습니다."; FAILED=$((FAILED + 1)); return; }
  if [[ "$SOURCE_BEFORE" == "$source_after" && "$INDEX_BEFORE" == "$index_after" ]]; then
    say "[PASS] 원본 source bytes·mode·symlink와 Git index raw bytes·staged entries 불변"
    PASSED=$((PASSED + 1))
  else
    say "[FAIL] 검증이 원본 source 또는 Git index raw bytes·staged entries를 변경했습니다."
    FAILED=$((FAILED + 1))
  fi
}

print_summary() {
  local result=$1
  {
    printf '\n============================================================\n'
    printf 'RESULT: %s\n' "$result"
    printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
    printf 'VERIFY LOG: %s\n' "$FINAL_LOG"
    printf '============================================================\n'
  } | tee -a "$FINAL_LOG"
}

finish() {
  local result=PASS exit_status=0
  check_original_state
  [[ $FAILED -eq 0 && $SKIPPED -eq 0 ]] \
    || { result=FAIL; exit_status=1; }
  cleanup
  trap - EXIT HUP INT TERM
  print_summary "$result"
  exit "$exit_status"
}

fatal() {
  say "[FAIL] $*"
  FAILED=$((FAILED + 1))
  finish
}

handle_signal() {
  local code=$1 name=$2
  trap - HUP INT TERM
  stop_active_tree
  say "[FAIL] $name 신호로 검증이 중단되었습니다."
  FAILED=$((FAILED + 1))
  check_original_state
  cleanup
  trap - EXIT
  print_summary FAIL
  exit "$code"
}

trap cleanup EXIT
trap 'handle_signal 129 HUP' HUP
trap 'handle_signal 130 INT' INT
trap 'handle_signal 143 TERM' TERM

run_managed() {
  "$@" >>"$FINAL_LOG" 2>&1 &
  ACTIVE_PID=$!
  local status
  wait "$ACTIVE_PID"
  status=$?
  ACTIVE_PID=
  return "$status"
}

run_check() {
  local label=$1
  shift
  {
    printf '\n============================================================\n'
    printf 'CHECK: %s\n' "$label"
    printf 'COMMAND:'
    printf ' %q' "$@"
    printf '\n============================================================\n'
  } >>"$FINAL_LOG"
  if run_managed "$@"; then
    say "[PASS] $label"
    PASSED=$((PASSED + 1))
  else
    local status=$?
    say "[FAIL] $label (exit=$status)"
    FAILED=$((FAILED + 1))
  fi
}

[[ "$PWD" == "$ROOT" ]] || fatal "저장소 루트에서 ./verify.sh를 실행해야 합니다."
command -v pgrep >/dev/null 2>&1 || fatal "자식 프로세스 정리를 위해 pgrep이 필요합니다."
[[ -f "$MARKER" ]] || fatal "준비 상태가 없습니다. 먼저 make prepare를 실행하십시오."

SOURCE_BEFORE=$(python3 "$ROOT/scripts/guide_state.py" capture "$ROOT") \
  || fatal "검증 전 source 상태를 기록하지 못했습니다."
PREPARATION_FINGERPRINT=$(python3 "$ROOT/scripts/guide_state.py" preparation-capture "$ROOT") \
  || fatal "검증 전 준비 fingerprint를 기록하지 못했습니다."
INDEX_BEFORE=$(python3 "$ROOT/scripts/guide_state.py" index-state "$ROOT") \
  || fatal "검증 전 Git index raw bytes와 staged entries를 기록하지 못했습니다."
python3 "$ROOT/scripts/guide_state.py" validate-marker "$MARKER" "$PREPARATION_FINGERPRINT" \
  >>"$FINAL_LOG" 2>&1 \
  || fatal "준비 상태가 없거나 손상되었거나 현재 curriculum source와 맞지 않습니다. make prepare를 다시 실행하십시오."

MAVEN_USER_HOME=$(
  python3 "$ROOT/scripts/guide_state.py" marker-field \
    "$MARKER" "$PREPARATION_FINGERPRINT" maven_user_home
) || fatal "준비된 Maven user home을 읽지 못했습니다."
GUIDE_MAVEN_REPOSITORY=$(
  python3 "$ROOT/scripts/guide_state.py" marker-field \
    "$MARKER" "$PREPARATION_FINGERPRINT" maven_repository
) || fatal "준비된 Maven repository를 읽지 못했습니다."
export MAVEN_USER_HOME GUIDE_MAVEN_REPOSITORY

WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/guide-java-verify.XXXXXX") \
  || fatal "검증용 임시 디렉터리를 만들지 못했습니다."
WORK_TREE="$WORK_ROOT/repository"
mkdir -p "$WORK_TREE"
python3 "$ROOT/scripts/guide_state.py" copy "$ROOT" "$WORK_TREE" \
  >>"$FINAL_LOG" 2>&1 \
  || fatal "현재 working tree를 격리 디렉터리로 복사하지 못했습니다."
COPIED_STATE=$(python3 "$WORK_TREE/scripts/guide_state.py" capture "$WORK_TREE") \
  || fatal "복사된 source 상태를 기록하지 못했습니다."
[[ "$COPIED_STATE" == "$SOURCE_BEFORE" ]] \
  || fatal "격리 복사본이 원본 working tree와 일치하지 않습니다."
say "[PASS] source fingerprint와 격리 복사 확인: $SOURCE_BEFORE"
PASSED=$((PASSED + 1))

cd "$WORK_TREE" || fatal "격리 복사본으로 이동하지 못했습니다."
run_check "개발 환경과 버전" ./scripts/preflight.sh
run_check "문서·정확한 tree·실습 계약" python3 scripts/validate.py
run_check "validator와 검증 계약 mutant suite" python3 scripts/test_validate.py
run_check "셸 문법" bash -c \
  'while IFS= read -r -d "" script; do bash -n "$script" || exit 1; done < <(find . -type f -name "*.sh" -not -path "./.workspace/*" -not -path "*/target/*" -print0)'
run_check "JDK 21에서 release 17 직접 컴파일" ./scripts/smoke-javac.sh
run_check "Maven reference reactor와 품질 검사" ./scripts/mvn-guide.sh clean verify

run_check "first-program skeleton 지정 실패" ./scripts/verify-skeletons.sh first-program
run_check "value-object-contract skeleton 지정 실패" ./scripts/verify-skeletons.sh value-object-contract
run_check "concurrent-state-update skeleton 지정 실패" ./scripts/verify-skeletons.sh concurrent-state-update
run_check "executor-lifecycle skeleton 지정 실패" ./scripts/verify-skeletons.sh executor-lifecycle
run_check "state-and-effect-testing skeleton 지정 실패" ./scripts/verify-skeletons.sh state-and-effect-testing
run_check "concurrent-job-ledger skeleton 지정 실패" ./scripts/verify-skeletons.sh concurrent-job-ledger

run_check "격리된 Maven 저장소 실습" \
  ./exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh
run_check "JFR 실행기 기록" ./scripts/record-executor-jfr.sh
run_check "검증 복사본 생성물 정리" make clean
run_check "정리 뒤 정확한 tree 검사" python3 scripts/validate.py

finish
