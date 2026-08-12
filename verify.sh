#!/bin/sh

ROOT=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
cd "$ROOT" || exit 2

EXPECTED_PNPM=$(node -p 'require("./package.json").packageManager.split("@").at(-1)') || exit 2
if [ -x "$ROOT/.guide-tools/bin/pnpm" ]
then
    PNPM="$ROOT/.guide-tools/bin/pnpm"
    PATH="$ROOT/.guide-tools/bin:$PATH"
    export PATH
elif command -v pnpm >/dev/null 2>&1
then
    PNPM=$(command -v pnpm)
else
    printf 'VERIFY ERROR: pnpm 실행기를 찾을 수 없습니다. 먼저 ./prepare.sh를 실행하십시오.\n' >&2
    exit 2
fi
if [ "$("$PNPM" --version 2>/dev/null)" != "$EXPECTED_PNPM" ]
then
    printf 'VERIFY ERROR: pnpm %s가 필요합니다. 먼저 ./prepare.sh를 실행하십시오.\n' "$EXPECTED_PNPM" >&2
    exit 2
fi

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG=${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-web-app-verify-${TIMESTAMP}-$$.log}
case "$LOG" in
    /*) ;;
    *)
        printf 'VERIFY ERROR: VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다: %s\n' "$LOG" >&2
        exit 2
        ;;
esac
case "$LOG" in
    "$ROOT"|"$ROOT"/*)
        printf 'VERIFY ERROR: VERIFY_LOG는 저장소 밖의 경로여야 합니다: %s\n' "$LOG" >&2
        exit 2
        ;;
esac
LOG_PARENT=$(dirname "$LOG")
if [ ! -d "$LOG_PARENT" ]
then
    printf 'VERIFY ERROR: 저장소 밖의 로그 디렉터리를 먼저 만들어야 합니다: %s\n' "$LOG_PARENT" >&2
    exit 2
fi
LOG_DIRECTORY=$(CDPATH= cd "$LOG_PARENT" && pwd -P) || {
    printf 'VERIFY ERROR: 로그 디렉터리를 확인할 수 없습니다: %s\n' "$LOG_PARENT" >&2
    exit 2
}
LOG="$LOG_DIRECTORY/$(basename "$LOG")"
case "$LOG" in
    "$ROOT"|"$ROOT"/*)
        printf 'VERIFY ERROR: VERIFY_LOG는 저장소 밖의 경로여야 합니다: %s\n' "$LOG" >&2
        exit 2
        ;;
esac
if [ -e "$LOG" ] || [ -L "$LOG" ]
then
    printf 'VERIFY ERROR: 기존 파일이나 symbolic link를 VERIFY_LOG로 덮어쓰지 않습니다: %s\n' "$LOG" >&2
    exit 2
fi
FAILED=0
CLEANED=0

( set -C; : > "$LOG" ) 2>/dev/null || {
    printf 'VERIFY ERROR: 새 verify log를 안전하게 만들 수 없습니다: %s\n' "$LOG" >&2
    exit 2
}

SOURCE_STATE_DIRECTORY=$(mktemp -d "${TMPDIR:-/tmp}/guide-web-app-source-state.XXXXXX") || {
    printf 'VERIFY ERROR: 소스 상태를 기록할 임시 디렉터리를 만들 수 없습니다.\n' >&2
    exit 2
}
SOURCE_STATE_BEFORE="$SOURCE_STATE_DIRECTORY/source-before.sha256"
SOURCE_STATE_AFTER="$SOURCE_STATE_DIRECTORY/source-after.sha256"
if ! node scripts/capture-source-state.mjs > "$SOURCE_STATE_BEFORE" 2>> "$LOG"
then
    rm -rf -- "$SOURCE_STATE_DIRECTORY"
    printf 'VERIFY ERROR: 검증 전 tracked source 상태를 기록할 수 없습니다.\n' >&2
    exit 2
fi

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
            \( -path './.git' -o -path './exercises/*/work' -o -path '*/node_modules' -o -path '*/.pnpm-store' \) \
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
            \( -path './.git' -o -path './exercises/*/work' -o -path '*/node_modules' -o -path '*/.pnpm-store' \) \
            -prune -o \
            -type f \
            \( -name '*.tsbuildinfo' -o -name 'next-env.d.ts' \) \
            -exec rm -f {} + \
            >> "$LOG" 2>&1
    then
        printf '[PASS] clean\n' | tee -a "$LOG"
    else
        status=$?
        printf '[FAIL] clean (exit=%d)\n' "$status" | tee -a "$LOG"
        FAILED=1
    fi

    if \
        node scripts/capture-source-state.mjs > "$SOURCE_STATE_AFTER" 2>> "$LOG" \
        && cmp -s "$SOURCE_STATE_BEFORE" "$SOURCE_STATE_AFTER"
    then
        printf '[PASS] source-stability\n' | tee -a "$LOG"
    else
        printf '[FAIL] source-stability (source worktree changed during verification)\n' | tee -a "$LOG"
        {
            printf '\n--- source state before/after ---\n'
            printf 'before: %s\n' "$(cat "$SOURCE_STATE_BEFORE")"
            printf 'after:  %s\n' "$(cat "$SOURCE_STATE_AFTER")"
            printf '\n--- current source changes ---\n'
            git status --short --untracked-files=all
            git --no-pager diff --stat HEAD --
        } >> "$LOG" 2>&1
        FAILED=1
    fi
    rm -rf -- "$SOURCE_STATE_DIRECTORY"
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
run "pnpm"           "$PNPM" --version
run "docker-compose" docker compose version

# ----------------------------------------------------------------------
# Repository structure and documentation contracts
# ----------------------------------------------------------------------

run "structure" \
    node scripts/verify-guide-structure.mjs

run "learning-contract" \
    "$PNPM" check:learning-contract

run "workspace-helper" \
    node scripts/test-new-workspace.mjs

run "verify-log-policy" \
    node scripts/test-verify-log-policy.mjs

run "browser-harness-failure-cleanup" \
    node scripts/test-browser-harness.mjs

run "links" \
    node scripts/verify-links.mjs

run "snippets" \
    node scripts/verify-snippets.mjs

run "capstone-specs" \
    node exercises/collaboration-board/checks/verify-stage-specs.mjs

run "collaboration-structure" \
    node scripts/verify-collaboration-board.mjs

run "exercise-contracts" \
    node scripts/verify-exercise-contracts.mjs

run "capstone-verifier-quality" \
    node exercises/collaboration-board/checks/verify-work-verifier.mjs --database

run "capstone-postgresql-runner-quality" \
    node scripts/verify-collaboration-postgresql.mjs --self-test

run "walkthrough-patches" \
    "$PNPM" check:walkthrough

run "checker-quality" \
    node scripts/verify-checker-quality.mjs

# ----------------------------------------------------------------------
# Reference implementations
# ----------------------------------------------------------------------

run "foundations" \
    "$PNPM" verify:foundations

run "runtime-workspace" \
    "$PNPM" verify:runtime

run "react-nextjs" \
    "$PNPM" verify:react

run "fastify-zod-api" \
    "$PNPM" verify:api

run "postgresql-kysely" \
    "$PNPM" verify:database

run "security" \
    "$PNPM" verify:security

run "websocket" \
    "$PNPM" verify:realtime

run "testing" \
    "$PNPM" verify:testing

run "collaboration-board" \
    "$PNPM" verify:collaboration

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
