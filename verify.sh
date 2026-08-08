#!/bin/sh

ROOT=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
cd "$ROOT" || exit 2

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG=${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-web-app-verify-${TIMESTAMP}-$$.log}
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
    "$ROOT"|"$ROOT"/*)
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
        printf 'COMMAND: %s\n' "$*"
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

    if \
        find . \
            \( -path './.git' -o -path '*/node_modules' -o -path '*/.pnpm-store' \) \
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
            \( -path './.git' -o -path '*/node_modules' -o -path '*/.pnpm-store' \) \
            -prune -o \
            -type f \
            -name '*.tsbuildinfo' \
            -exec rm -f {} + \
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
    printf 'guide-web-applications verification\n'
    printf '============================================================\n'
    printf 'PWD: %s\n' "$(pwd)"
    printf 'CHROMIUM_PATH: %s\n' "${CHROMIUM_PATH:-<auto-detect>}"
} >> "$LOG"

# ----------------------------------------------------------------------
# Environment
# ----------------------------------------------------------------------

run "git"            git --version
run "node"           node --version
run "pnpm"           pnpm --version
run "docker-compose" docker compose version

# ----------------------------------------------------------------------
# Repository structure and documentation contracts
# ----------------------------------------------------------------------

run "structure" \
    node scripts/verify-guide-structure.mjs

run "links" \
    node scripts/verify-links.mjs

run "snippets" \
    node scripts/verify-snippets.mjs

run "capstone-specs" \
    node exercises/collaboration-board/checks/verify-stage-specs.mjs

run "collaboration-structure" \
    node scripts/verify-collaboration-board.mjs

run "walkthrough-patches" \
    pnpm check:walkthrough

# ----------------------------------------------------------------------
# Reference implementations
# ----------------------------------------------------------------------

run "foundations" \
    pnpm verify:foundations

run "runtime-workspace" \
    pnpm verify:runtime

run "react-nextjs" \
    pnpm verify:react

run "fastify-zod-api" \
    pnpm verify:api

run "postgresql-kysely" \
    pnpm verify:database

run "security" \
    pnpm verify:security

run "websocket" \
    pnpm verify:realtime

run "testing" \
    pnpm verify:testing

run "collaboration-board" \
    pnpm verify:collaboration

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
