#!/bin/sh

# guide-frontend-react-nextjs verification
#
# 이 스크립트는 현재 저장소가 실제 package.json으로 제공하는 검증 계약을
# 단계별로 실행한 뒤 canonical `pnpm verify`까지 다시 확인합니다.
#
# 별도 scripts/verify-docs.mjs 또는 scripts/smoke-production.mjs의 존재를
# 가정하지 않습니다.
#
# 학습자가 작성한 exercises/project-catalog/workspace/는
# 생성·수정·삭제하지 않습니다.
#
# 결과 로그는 저장소 밖의 임시 경로에 남고 VERIFY_LOG로 바꿀 수 있습니다.

command -v git >/dev/null 2>&1 || {
    printf 'ERROR: git을 찾을 수 없습니다.\n' >&2
    exit 1
}

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
    printf 'ERROR: Git 저장소 안에서 실행해야 합니다.\n' >&2
    exit 1
}

cd "$REPO_ROOT"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG=${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-web-front-react-nextjs-verify-${TIMESTAMP}-$$.log}
case "$LOG" in
    /*) ;;
    *)
        printf 'VERIFY ERROR: VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다: %s\n' "$LOG" >&2
        exit 2
        ;;
esac
mkdir -p "$(dirname "$LOG")" 2>/dev/null || {
    printf 'VERIFY ERROR: 로그 디렉터리를 만들 수 없습니다: %s\n' "$(dirname "$LOG")" >&2
    exit 2
}
LOG_DIRECTORY=$(CDPATH= cd "$(dirname "$LOG")" && pwd -P) || {
    printf 'VERIFY ERROR: 로그 디렉터리를 확인할 수 없습니다: %s\n' "$(dirname "$LOG")" >&2
    exit 2
}
LOG="$LOG_DIRECTORY/$(basename "$LOG")"
case "$LOG" in
    "$REPO_ROOT"|"$REPO_ROOT"/*)
        printf 'VERIFY ERROR: VERIFY_LOG는 저장소 밖의 경로여야 합니다: %s\n' "$LOG" >&2
        exit 2
        ;;
esac
FAILED=0
CLEANED=0

: > "$LOG"

run()
{
    name=$1
    shift

    {
        printf '\n============================================================\n'
        printf 'CHECK: %s\n' "$name"
        printf 'COMMAND:'
        for arg in "$@"
        do
            printf ' %s' "$arg"
        done
        printf '\n'
        printf '============================================================\n'
    } >> "$LOG"

    if "$@" >> "$LOG" 2>&1
    then
        printf '[PASS] %s\n' "$name" | tee -a "$LOG"
    else
        status=$?
        printf '[FAIL] %s (exit=%d)\n' "$name" "$status" | tee -a "$LOG"
        FAILED=1
    fi
}

check_structure()
{
    for path in \
        docs/00-roadmap-and-prerequisites.md \
        docs/01-project-onboarding.md \
        docs/02-ui-and-state-architecture.md \
        docs/03-nextjs-data-effects-and-concurrency.md \
        docs/04-testing-accessibility-and-performance.md \
        docs/05-production-runtime-contract.md \
        docs/90-practical-checklist.md \
        exercises/project-catalog/README.md \
        exercises/project-catalog/reference/package.json \
        exercises/project-catalog/skeleton/README.md \
        scripts/verify-skeleton.mjs \
        scripts/clean-generated.mjs
    do
        [ -e "$path" ] || {
            printf 'missing required path: %s\n' "$path" >&2
            return 1
        }
    done

    for path in \
        docs/00-browser-and-react-foundations.md \
        docs/02-ui-architecture.md \
        docs/03-state-data-effects.md \
        docs/04-testing-performance-deployment.md \
        reference/practical-checklist.md \
        exercises/project-catalog/reference/tests/e2e/catalog.spec.ts
    do
        [ ! -e "$path" ] || {
            printf 'obsolete path still exists: %s\n' "$path" >&2
            return 1
        }
    done
}

cleanup()
{
    if [ "$CLEANED" -eq 1 ]
    then
        return
    fi

    CLEANED=1

    {
        printf '\n============================================================\n'
        printf 'CLEAN\n'
        printf '============================================================\n'
    } >> "$LOG"

    # node_modules와 학습자 workspace는 보존한다.
    # 검증 과정에서 생긴 build/test 산출물만 제거한다.
    if \
        find . \
            \( -path './.git' -o -path '*/node_modules' -o -path './exercises/project-catalog/workspace' \) \
            -prune -o \
            -type d \
            \( \
                -name '.next' -o \
                -name '.turbo' -o \
                -name 'coverage' -o \
                -name 'playwright-report' -o \
                -name 'test-results' \
            \) \
            -prune \
            -exec rm -rf {} + \
            >> "$LOG" 2>&1 \
        && \
        find . \
            \( -path './.git' -o -path '*/node_modules' -o -path './exercises/project-catalog/workspace' \) \
            -prune -o \
            -type f \
            \( -name '*.tsbuildinfo' -o -name '.eslintcache' \) \
            -exec rm -f {} + \
            >> "$LOG" 2>&1 \
        && \
        rm -f ./exercises/project-catalog/reference/next-env.d.ts \
            >> "$LOG" 2>&1
    then
        printf '[PASS] clean\n' | tee -a "$LOG"
    else
        status=$?
        printf '[FAIL] clean (exit=%d)\n' "$status" | tee -a "$LOG"
        FAILED=1
    fi
}

handle_signal()
{
    code=$1
    name=$2

    printf '[FAIL] interrupted by %s\n' "$name" | tee -a "$LOG"
    FAILED=1

    cleanup

    trap - EXIT HUP INT TERM
    printf 'VERIFY LOG: %s\n' "$LOG" | tee -a "$LOG"
    exit "$code"
}

trap cleanup EXIT
trap 'handle_signal 129 HUP' HUP
trap 'handle_signal 130 INT' INT
trap 'handle_signal 143 TERM' TERM

{
    printf 'guide-frontend-react-nextjs verification\n'
    printf '============================================================\n'
    printf 'PWD: %s\n' "$(pwd)"
    printf 'NODE: %s\n' "$(node --version 2>/dev/null || printf '<missing>')"
    printf 'PNPM: %s\n' "$(pnpm --version 2>/dev/null || printf '<missing>')"
} >> "$LOG"

# ----------------------------------------------------------------------
# Environment
# ----------------------------------------------------------------------

run "git"  git --version
run "node" node --version
run "pnpm" pnpm --version

# ----------------------------------------------------------------------
# Repository structure
# ----------------------------------------------------------------------

run "structure" \
    check_structure

# ----------------------------------------------------------------------
# Existing repository verification contracts
# ----------------------------------------------------------------------

run "reference-typecheck-unit" \
    pnpm check:reference

run "skeleton-contract" \
    pnpm check:skeleton

run "combined-check" \
    pnpm check

run "production-build" \
    pnpm build

run "production-browser" \
    pnpm test:e2e

# ----------------------------------------------------------------------
# Canonical integration contract
# ----------------------------------------------------------------------

# 위 검사는 실패 위치를 세분화하기 위한 것이다.
# 마지막에 저장소가 문서화한 한 번의 통합 명령도 다시 실행해
# 검사가 순서에 의존하지 않고 반복 실행 가능한지 확인한다.
run "canonical-pnpm-verify" \
    pnpm verify

# ----------------------------------------------------------------------
# Repository hygiene
# ----------------------------------------------------------------------

run "diff-check" \
    git diff --check

trap - EXIT HUP INT TERM
cleanup

printf '\n============================================================\n' >> "$LOG"

if [ "$FAILED" -eq 0 ]
then
    printf 'RESULT: PASS\n' | tee -a "$LOG"
    printf 'VERIFY LOG: %s\n' "$LOG" | tee -a "$LOG"
    exit 0
fi

printf 'RESULT: FAIL\n' | tee -a "$LOG"
printf 'VERIFY LOG: %s\n' "$LOG" | tee -a "$LOG"
exit 1
