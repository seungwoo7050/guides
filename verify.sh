#!/bin/sh
set -u

ROOT=$(CDPATH= cd "$(dirname "$0")" && pwd)
STATE_FILE="$ROOT/.guide-prepare.env"
case ${VERIFY_LOG:-} in
    '') FINAL_LOG="$ROOT/verify.log" ;;
    /*) FINAL_LOG=$VERIFY_LOG ;;
    *) FINAL_LOG="$ROOT/$VERIFY_LOG" ;;
esac
REQUIRE_OPTIONAL=${VERIFY_REQUIRE_OPTIONAL:-0}
WORK_ROOT=
WORK_TREE=
LOG_TEMP=
CLEANED=0
PASSED=0
FAILED=0
SKIPPED=0
SOURCE_STATUS_AVAILABLE=0

say()
{
    printf '%s\n' "$*"
}

die()
{
    printf 'verify.sh 실패: %s\n' "$*" >&2
    exit 1
}

cleanup()
{
    if [ "$CLEANED" -eq 1 ]; then
        return
    fi
    CLEANED=1
    if [ -n "${WORK_ROOT:-}" ] && [ -d "$WORK_ROOT" ]; then
        rm -rf "$WORK_ROOT"
    fi
}

on_exit()
{
    status=$?
    cleanup
    trap - EXIT
    exit "$status"
}

on_signal()
{
    code=$1
    name=$2
    printf '\nverify.sh가 %s 신호로 중단되었습니다. 임시 산출물을 정리합니다.\n' "$name" >&2
    if [ -n "${LOG_TEMP:-}" ] && [ -f "$LOG_TEMP" ]; then
        mkdir -p "$(dirname "$FINAL_LOG")" 2>/dev/null || true
        cp "$LOG_TEMP" "$FINAL_LOG" 2>/dev/null || true
    fi
    exit "$code"
}

trap on_exit EXIT
trap 'on_signal 129 HUP' HUP
trap 'on_signal 130 INT' INT
trap 'on_signal 143 TERM' TERM

[ -f "$STATE_FILE" ] || die '먼저 저장소 루트에서 ./prepare.sh를 실행하세요'
# prepare.sh가 shell-safe 형식으로 생성한 저장소 내부 상태 파일입니다.
# shellcheck disable=SC1090
. "$STATE_FILE"

[ "${GUIDE_PREPARED:-0}" = 1 ] || die '준비 상태 파일이 올바르지 않습니다. ./prepare.sh를 다시 실행하세요'

export CC=${GUIDE_CC:-cc}
export ASAN_OPTIONS=${GUIDE_ASAN_OPTIONS:-halt_on_error=1:detect_leaks=0}
export ASAN_PROCESS_OPTIONS=${GUIDE_ASAN_PROCESS_OPTIONS:-halt_on_error=1:detect_leaks=0}
export UBSAN_OPTIONS=${GUIDE_UBSAN_OPTIONS:-halt_on_error=1:print_stacktrace=1}
export TSAN_OPTIONS=${GUIDE_TSAN_OPTIONS:-halt_on_error=1}
export READLINE_CPPFLAGS=${GUIDE_READLINE_CPPFLAGS:-}
export READLINE_LDFLAGS=${GUIDE_READLINE_LDFLAGS:-}
export READLINE_LDLIBS=${GUIDE_READLINE_LDLIBS:--lreadline}

WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/guide-c-verify.XXXXXX") || die '임시 디렉터리를 만들 수 없습니다'
WORK_TREE="$WORK_ROOT/repository"
LOG_TEMP="$WORK_ROOT/verify.log"
mkdir -p "$WORK_TREE"
: >"$LOG_TEMP"

if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$ROOT" status --porcelain=v1 --untracked-files=all >"$WORK_ROOT/status-before"
    SOURCE_STATUS_AVAILABLE=1
fi

say '==> 검증용 임시 저장소 복사'
cp -R "$ROOT/." "$WORK_TREE/" || die '저장소를 임시 작업 디렉터리에 복사할 수 없습니다'
rm -rf "$WORK_TREE/.git" "$WORK_TREE/.guide-prepare.env" "$WORK_TREE/verify.log"
cd "$WORK_TREE" || die '임시 저장소에 들어갈 수 없습니다'

print_header()
{
    label=$1
    command_text=$2
    {
        printf '\n============================================================\n'
        printf 'CHECK: %s\n' "$label"
        printf 'COMMAND: %s\n' "$command_text"
        printf '============================================================\n'
    } | tee -a "$LOG_TEMP"
}

run_check()
{
    label=$1
    shift
    command_text=$*
    output="$WORK_ROOT/check-output"

    print_header "$label" "$command_text"
    "$@" >"$output" 2>&1
    status=$?
    cat "$output"
    cat "$output" >>"$LOG_TEMP"
    if [ "$status" -eq 0 ]; then
        printf '[PASS] %s\n' "$label" | tee -a "$LOG_TEMP"
        PASSED=$((PASSED + 1))
    else
        printf '[FAIL] %s (exit=%s)\n' "$label" "$status" | tee -a "$LOG_TEMP" >&2
        FAILED=$((FAILED + 1))
    fi
    rm -f "$output"
}

skip_check()
{
    label=$1
    reason=$2
    print_header "$label" '선택 기능 확인'
    printf '[SKIP] %s: %s\n' "$label" "$reason" | tee -a "$LOG_TEMP"
    SKIPPED=$((SKIPPED + 1))
    if [ "$REQUIRE_OPTIONAL" = 1 ]; then
        printf '[FAIL] 선택 기능이 필수로 요청되었습니다: %s\n' "$label" | tee -a "$LOG_TEMP" >&2
        FAILED=$((FAILED + 1))
    fi
}

soft_skip_check()
{
    label=$1
    reason=$2
    print_header "$label" '환경 정보 확인'
    printf '[SKIP] %s: %s\n' "$label" "$reason" | tee -a "$LOG_TEMP"
    SKIPPED=$((SKIPPED + 1))
}

run_check 'initial-clean' make clean
run_check 'clean-source-tree' python3 scripts/validate_repository.py --clean
run_check 'repository-structure' python3 scripts/validate_repository.py
run_check 'documentation' make docs-check
run_check 'examples' make examples-check
run_check 'reference-implementations' make exercises-check
run_check 'skeleton-contract' make quality-check

if [ "${GUIDE_HAVE_SANITIZERS:-0}" = 1 ]; then
    run_check 'asan-ubsan' make sanitize
else
    skip_check 'asan-ubsan' 'prepare.sh probe에서 지원되지 않았습니다'
fi

if [ "${GUIDE_HAVE_TSAN:-0}" = 1 ]; then
    run_check 'thread-sanitizer' make thread-sanitize
else
    skip_check 'thread-sanitizer' 'prepare.sh probe에서 지원되지 않았습니다'
fi

if [ "${GUIDE_HAVE_READLINE:-0}" = 1 ]; then
    run_check 'readline' make readline-check
else
    skip_check 'readline' 'Readline 개발 파일을 찾지 못했습니다'
fi

run_check 'post-check-clean' make clean
run_check 'post-check-artifacts' python3 scripts/validate_repository.py --clean
run_check 'clean-rebuild' make check
run_check 'final-clean' make clean
run_check 'final-artifacts' python3 scripts/validate_repository.py --clean

if [ "$SOURCE_STATUS_AVAILABLE" -eq 1 ]; then
    git -C "$ROOT" status --porcelain=v1 --untracked-files=all >"$WORK_ROOT/status-after"
    print_header 'source-tree-unchanged' 'git status before/after comparison'
    if cmp -s "$WORK_ROOT/status-before" "$WORK_ROOT/status-after"; then
        printf '[PASS] source-tree-unchanged\n' | tee -a "$LOG_TEMP"
        PASSED=$((PASSED + 1))
    else
        printf 'verify.sh 실행 전후의 원본 저장소 상태가 다릅니다.\n' | tee -a "$LOG_TEMP" >&2
        diff -u "$WORK_ROOT/status-before" "$WORK_ROOT/status-after" | tee -a "$LOG_TEMP" >&2 || true
        printf '[FAIL] source-tree-unchanged\n' | tee -a "$LOG_TEMP" >&2
        FAILED=$((FAILED + 1))
    fi
else
    soft_skip_check 'source-tree-unchanged' 'Git 작업 트리가 아니어서 비교하지 못했습니다'
fi

{
    printf '\n============================================================\n'
    printf 'RESULT: '
    if [ "$FAILED" -eq 0 ]; then
        printf 'PASS\n'
    else
        printf 'FAIL\n'
    fi
    printf 'passed=%s failed=%s skipped=%s\n' "$PASSED" "$FAILED" "$SKIPPED"
    printf 'baseline=%s\n' "${GUIDE_BASELINE_SHA:-unknown}"
    printf 'compiler=%s\n' "${GUIDE_CC:-unknown}"
    printf '============================================================\n'
} | tee -a "$LOG_TEMP"

if [ "$FAILED" -ne 0 ]; then
    log_parent=$(dirname "$FINAL_LOG")
    mkdir -p "$log_parent" 2>/dev/null || true
    if cp "$LOG_TEMP" "$FINAL_LOG"; then
        printf '전체 로그: %s\n' "$FINAL_LOG" >&2
    else
        printf '전체 로그를 복사하지 못했습니다: %s\n' "$FINAL_LOG" >&2
    fi
    exit 1
fi

rm -f "$FINAL_LOG"
exit 0
