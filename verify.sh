#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd -P)
MARKER="$ROOT/.guide/java/prepared.json"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REQUESTED_LOG=${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-java-verify-${TIMESTAMP}-$$.log}
WORK_ROOT=
WORK_TREE=
PASSED=0
FAILED=0
SKIPPED=0
CLEANED=0

resolve_log() {
  [[ "$REQUESTED_LOG" == /* ]] \
    || { printf '[FAIL] VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다: %s\n' "$REQUESTED_LOG" >&2; exit 2; }
  python3 - "$ROOT" "$REQUESTED_LOG" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
requested = Path(sys.argv[2])
requested.parent.mkdir(parents=True, exist_ok=True)
resolved = requested.resolve(strict=False)
if resolved == root or root in resolved.parents:
    raise SystemExit(f"[FAIL] VERIFY_LOG는 저장소 밖이어야 합니다: {resolved}")
print(resolved)
PY
}

FINAL_LOG=$(resolve_log) || exit 2
: >"$FINAL_LOG" || { printf '[FAIL] 로그를 쓸 수 없습니다: %s\n' "$FINAL_LOG" >&2; exit 2; }

say() {
  printf '%s\n' "$*" | tee -a "$FINAL_LOG"
}

cleanup() {
  [[ $CLEANED -eq 0 ]] || return
  CLEANED=1
  [[ -z "${WORK_ROOT:-}" || ! -d "$WORK_ROOT" ]] || rm -rf "$WORK_ROOT"
}

finish() {
  local result=PASS exit_status=0
  [[ $FAILED -eq 0 && $SKIPPED -eq 0 ]] || { result=FAIL; exit_status=1; }
  {
    printf '\n============================================================\n'
    printf 'RESULT: %s\n' "$result"
    printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
    printf 'VERIFY LOG: %s\n' "$FINAL_LOG"
    printf '============================================================\n'
  } | tee -a "$FINAL_LOG"
  cleanup
  trap - EXIT HUP INT TERM
  exit "$exit_status"
}

fatal() {
  say "[FAIL] $*"
  FAILED=$((FAILED + 1))
  finish
}

handle_signal() {
  local code=$1 name=$2
  say "[FAIL] $name 신호로 검증이 중단되었습니다."
  FAILED=$((FAILED + 1))
  cleanup
  trap - EXIT HUP INT TERM
  {
    printf 'RESULT: FAIL\n'
    printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
    printf 'VERIFY LOG: %s\n' "$FINAL_LOG"
  } | tee -a "$FINAL_LOG"
  exit "$code"
}

trap cleanup EXIT
trap 'handle_signal 129 HUP' HUP
trap 'handle_signal 130 INT' INT
trap 'handle_signal 143 TERM' TERM

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
  if "$@" >>"$FINAL_LOG" 2>&1; then
    say "[PASS] $label"
    PASSED=$((PASSED + 1))
  else
    local status=$?
    say "[FAIL] $label (exit=$status)"
    FAILED=$((FAILED + 1))
  fi
}

expect_skeleton_failure() {
  local label=$1
  local pom=$2
  local output="$WORK_ROOT/skeleton-${label}.log"
  {
    printf '\n============================================================\n'
    printf 'CHECK: skeleton-%s\n' "$label"
    printf '============================================================\n'
  } >>"$FINAL_LOG"
  "$WORK_TREE/scripts/mvn-guide.sh" -f "$WORK_TREE/$pom" test >"$output" 2>&1
  local status=$?
  cat "$output" >>"$FINAL_LOG"
  if [[ $status -ne 0 ]] \
    && grep -Eq 'Failures:[[:space:]]*[1-9][0-9]*' "$output" \
    && grep -Eq 'AssertionFailedError|AssertionError' "$output" \
    && ! grep -Eq 'COMPILATION ERROR|NoClassDefFoundError|Could not resolve dependencies' "$output"; then
    say "[PASS] $label skeleton이 학습 계약 단언으로 실패"
    PASSED=$((PASSED + 1))
  else
    say "[FAIL] $label skeleton 실패 원인이 학습 계약 단언이 아닙니다."
    FAILED=$((FAILED + 1))
  fi
}

[[ "$PWD" == "$ROOT" ]] || fatal "저장소 루트에서 ./verify.sh를 실행해야 합니다."
[[ -f "$MARKER" ]] || fatal "준비 상태가 없습니다. 먼저 ./prepare.sh를 실행하십시오."

SOURCE_BEFORE=$(python3 "$ROOT/scripts/guide_state.py" capture "$ROOT") \
  || fatal "검증 전 source 상태를 기록하지 못했습니다."
INDEX_BEFORE=$(git -C "$ROOT" write-tree) \
  || fatal "검증 전 Git index 상태를 기록하지 못했습니다."
python3 "$ROOT/scripts/guide_state.py" validate-marker "$MARKER" "$SOURCE_BEFORE" \
  >>"$FINAL_LOG" 2>&1 || fatal "준비 상태가 없거나 손상되었거나 현재 source와 맞지 않습니다. ./prepare.sh를 다시 실행하십시오."

MAVEN_USER_HOME=$(
  python3 "$ROOT/scripts/guide_state.py" marker-field \
    "$MARKER" "$SOURCE_BEFORE" maven_user_home
) || fatal "준비된 Maven user home을 읽지 못했습니다."
GUIDE_MAVEN_REPOSITORY=$(
  python3 "$ROOT/scripts/guide_state.py" marker-field \
    "$MARKER" "$SOURCE_BEFORE" maven_repository
) || fatal "준비된 Maven repository를 읽지 못했습니다."
export MAVEN_USER_HOME GUIDE_MAVEN_REPOSITORY

WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/guide-java-verify.XXXXXX") \
  || fatal "검증용 임시 디렉터리를 만들지 못했습니다."
WORK_TREE="$WORK_ROOT/repository"
mkdir -p "$WORK_TREE"
python3 "$ROOT/scripts/guide_state.py" copy "$ROOT" "$WORK_TREE" \
  >>"$FINAL_LOG" 2>&1 || fatal "현재 working tree를 격리 디렉터리로 복사하지 못했습니다."
COPIED_STATE=$(python3 "$WORK_TREE/scripts/guide_state.py" capture "$WORK_TREE") \
  || fatal "복사된 source 상태를 기록하지 못했습니다."
[[ "$COPIED_STATE" == "$SOURCE_BEFORE" ]] \
  || fatal "격리 복사본이 원본 working tree와 일치하지 않습니다."
say "[PASS] source fingerprint와 격리 복사 확인: $SOURCE_BEFORE"
PASSED=$((PASSED + 1))

cd "$WORK_TREE" || fatal "격리 복사본으로 이동하지 못했습니다."
run_check "개발 환경과 버전" ./scripts/preflight.sh
run_check "문서·정확한 tree·실습 계약" python3 scripts/validate.py
run_check "validator mutant suite" python3 scripts/test_validate.py
run_check "셸 문법" bash -c \
  'while IFS= read -r -d "" script; do bash -n "$script" || exit 1; done < <(find . -type f -name "*.sh" -not -path "*/target/*" -print0)'
run_check "JDK 21에서 release 17 직접 컴파일" ./scripts/smoke-javac.sh
run_check "Maven reference reactor와 품질 검사" ./scripts/mvn-guide.sh clean verify

expect_skeleton_failure first-program \
  exercises/01-language-and-domain/01-first-program/skeleton/pom.xml
expect_skeleton_failure value-object-contract \
  exercises/01-language-and-domain/02-value-object-contract/skeleton/pom.xml
expect_skeleton_failure concurrent-state-update \
  exercises/02-runtime-and-concurrency/01-concurrent-state-update/skeleton/pom.xml
expect_skeleton_failure executor-lifecycle \
  exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/pom.xml
expect_skeleton_failure state-and-effect-testing \
  exercises/03-build-test-and-evidence/02-state-and-effect-testing/skeleton/pom.xml
expect_skeleton_failure concurrent-job-ledger \
  exercises/04-capstone/01-concurrent-job-ledger/skeleton/pom.xml

run_check "격리된 Maven 저장소 실습" \
  ./exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh
run_check "JFR 실행기 기록" ./scripts/record-executor-jfr.sh
run_check "검증 복사본 생성물 정리" make clean
run_check "정리 뒤 정확한 tree 검사" python3 scripts/validate.py

SOURCE_AFTER=$(python3 "$ROOT/scripts/guide_state.py" capture "$ROOT") \
  || fatal "검증 후 source 상태를 기록하지 못했습니다."
INDEX_AFTER=$(git -C "$ROOT" write-tree) \
  || fatal "검증 후 Git index 상태를 기록하지 못했습니다."
if [[ "$SOURCE_BEFORE" == "$SOURCE_AFTER" && "$INDEX_BEFORE" == "$INDEX_AFTER" ]]; then
  say "[PASS] 원본 source bytes·mode·symlink·Git index 불변"
  PASSED=$((PASSED + 1))
else
  say "[FAIL] 검증이 원본 source 또는 Git index를 변경했습니다."
  FAILED=$((FAILED + 1))
fi

finish
