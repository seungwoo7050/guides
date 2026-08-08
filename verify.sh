#!/usr/bin/env bash

# Deliberately do not use `set -e`: every independent check should be recorded,
# and one failure should not hide later structural or cleanup failures.
set -uo pipefail
umask 022

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$SCRIPT_DIR"
cd "$ROOT"

FAILED=0
SKIPPED=0
WORKSPACES_CLEANED=0
ALL_CLEANED=0
CONTROL_ROOT=""
WORK_ROOT=""
SOURCE_BEFORE=""
TRACKED_STATUS_BEFORE=""
GIT_AVAILABLE=0

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG="${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-cpp-verify-${TIMESTAMP}-$$.log}"
case "$LOG" in
    /*) ;;
    *) LOG="$ROOT/$LOG" ;;
esac
mkdir -p "$(dirname "$LOG")" 2>/dev/null || {
    printf 'VERIFY ERROR: 로그 디렉터리를 만들 수 없습니다: %s\n' "$(dirname "$LOG")" >&2
    exit 2
}
LOG_DIRECTORY="$(cd "$(dirname "$LOG")" && pwd -P)" || {
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
: > "$LOG" || {
    printf 'VERIFY ERROR: 로그를 만들 수 없습니다: %s\n' "$LOG" >&2
    exit 2
}

log()
{
    printf '%s\n' "$*" | tee -a "$LOG"
}

section()
{
    {
        printf '\n============================================================\n'
        printf '%s\n' "$*"
        printf '============================================================\n'
    } | tee -a "$LOG"
}

format_command()
{
    local argument
    for argument in "$@"; do
        printf '%q ' "$argument"
    done
    printf '\n'
}

skip_check()
{
    local name=$1
    local reason=$2
    SKIPPED=$((SKIPPED + 1))
    printf '[SKIP] %s: %s\n' "$name" "$reason" | tee -a "$LOG"
}

run_with_timeout()
{
    local seconds=$1
    shift
    python3 "$ROOT/scripts/run_with_timeout.py" "$seconds" -- "$@"
}

run_check()
{
    local name=$1
    local seconds=$2
    shift 2

    {
        printf '\n------------------------------------------------------------\n'
        printf 'CHECK: %s\n' "$name"
        printf 'TIMEOUT: %ss\n' "$seconds"
        printf 'COMMAND: '
        format_command "$@"
        printf 'WORKDIR: %s\n' "$PWD"
        printf '%s\n' '------------------------------------------------------------'
    } >> "$LOG"

    run_with_timeout "$seconds" "$@" >> "$LOG" 2>&1
    local status=$?

    if [ "$status" -eq 0 ]; then
        printf '[PASS] %s\n' "$name" | tee -a "$LOG"
        return 0
    fi

    printf '[FAIL] %s (exit=%d)\n' "$name" "$status" | tee -a "$LOG"
    FAILED=1
    return "$status"
}

require_command()
{
    if ! command -v "$1" >/dev/null 2>&1; then
        printf '[FAIL] missing command: %s\n' "$1" | tee -a "$LOG"
        FAILED=1
        return 1
    fi
    return 0
}

validate_mode()
{
    local name=$1
    local value=$2
    case "$value" in
        auto|required|off) return 0 ;;
        *)
            log "[FAIL] $name must be auto|required|off, found: $value"
            FAILED=1
            return 1
            ;;
    esac
}

copy_repository()
{
    local destination=$1
    python3 - "$ROOT" "$destination" <<'PY'
from __future__ import annotations

import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1]).resolve()
destination = Path(sys.argv[2]).resolve()

ignored_exact = {
    ".git",
    "make-out.txt",
    "tree.txt",
    "before-verify.sh",
    "__pycache__",
    ".pytest_cache",
    ".guide-probes",
}
ignored_suffixes = (
    ".o",
    ".d",
    ".a",
    ".so",
    ".dylib",
    ".dll",
    ".exe",
    ".pyc",
    ".pyo",
    ".dSYM",
    ".log",
)


def ignore(_directory: str, names: list[str]) -> set[str]:
    result = set()
    for name in names:
        if name in ignored_exact or name == "build" or name.startswith("build-"):
            result.add(name)
        elif name.endswith(ignored_suffixes):
            result.add(name)
    return result


shutil.copytree(source, destination, symlinks=True, ignore=ignore)
PY
}

probe_sanitizer()
{
    local compiler=$1
    local kind=$2
    local directory=$3
    mkdir -p "$directory"

    case "$kind" in
        asan-ubsan)
            cat > "$directory/probe.cpp" <<'CPP'
#include <vector>
int main()
{
    std::vector<int> values{1, 2, 3};
    return values.at(1) == 2 ? 0 : 1;
}
CPP
            run_with_timeout 120 \
                "$compiler" -std=c++20 -pthread -fsanitize=address,undefined \
                -fno-omit-frame-pointer "$directory/probe.cpp" -o "$directory/probe" \
                >> "$LOG" 2>&1 || return 1
            run_with_timeout 60 env \
                ASAN_OPTIONS="${ASAN_OPTIONS:-$ASAN_DEFAULT}" \
                UBSAN_OPTIONS="${UBSAN_OPTIONS:-halt_on_error=1:print_stacktrace=1}" \
                "$directory/probe" >> "$LOG" 2>&1
            ;;
        tsan)
            cat > "$directory/probe.cpp" <<'CPP'
#include <mutex>
#include <thread>
int main()
{
    int value = 0;
    std::mutex mutex;
    std::thread first([&] { std::lock_guard<std::mutex> lock(mutex); ++value; });
    std::thread second([&] { std::lock_guard<std::mutex> lock(mutex); ++value; });
    first.join();
    second.join();
    return value == 2 ? 0 : 1;
}
CPP
            run_with_timeout 120 \
                "$compiler" -std=c++20 -pthread -fsanitize=thread \
                -fno-omit-frame-pointer "$directory/probe.cpp" -o "$directory/probe" \
                >> "$LOG" 2>&1 || return 1
            run_with_timeout 60 env \
                TSAN_OPTIONS="${TSAN_OPTIONS:-halt_on_error=1}" \
                "$directory/probe" >> "$LOG" 2>&1
            ;;
        *) return 2 ;;
    esac
}

clean_original()
{
    if [ ! -f "$ROOT/scripts/manage_artifacts.py" ]; then
        return
    fi
    # prepare.sh already runs the repository Makefile clean targets. verify.sh
    # never builds in the original tree, so cleanup here is deliberately
    # limited to the audited generated-artifact policy instead of executing
    # arbitrary build recipes against the user's source checkout.
    python3 "$ROOT/scripts/manage_artifacts.py" clean "$ROOT" >> "$LOG" 2>&1 || true
}

clean_workspaces()
{
    if [ "$WORKSPACES_CLEANED" -eq 1 ]; then
        return
    fi
    WORKSPACES_CLEANED=1

    section 'CLEANUP'
    clean_original
    if [ -n "$WORK_ROOT" ] && [ -d "$WORK_ROOT" ]; then
        rm -rf "$WORK_ROOT"
    fi

    if [ -f "$ROOT/scripts/manage_artifacts.py" ]; then
        if ! python3 "$ROOT/scripts/manage_artifacts.py" audit "$ROOT" >> "$LOG" 2>&1; then
            log '[FAIL] 원본 저장소에 생성 산출물이 남았습니다.'
            FAILED=1
        else
            log '[PASS] 원본 저장소 생성 산출물 정리'
        fi
    fi
}

cleanup_all()
{
    if [ "$ALL_CLEANED" -eq 1 ]; then
        return
    fi
    ALL_CLEANED=1
    clean_workspaces
    if [ -n "$CONTROL_ROOT" ] && [ -d "$CONTROL_ROOT" ]; then
        rm -rf "$CONTROL_ROOT"
    fi
}

on_signal()
{
    local code=$1
    trap - EXIT HUP INT TERM
    log "[INTERRUPTED] exit=$code"
    cleanup_all
    exit "$code"
}

trap cleanup_all EXIT
trap 'on_signal 129' HUP
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

section 'PREFLIGHT'
if [ ! -f README.md ] || [ ! -f Makefile ] || [ ! -x prepare.sh ] || [ ! -x verify.sh ]; then
    log '[FAIL] prepare.sh가 완료된 guide-cpp 저장소 루트가 아닙니다.'
    exit 1
fi

for command_name in bash make cmake ctest python3; do
    require_command "$command_name" || true
done

CXX_COMMAND="${CXX:-c++}"
case "$CXX_COMMAND" in
    *[[:space:]]*)
        log "[FAIL] CXX에는 단일 compiler 실행 경로만 지정해야 합니다: $CXX_COMMAND"
        FAILED=1
        ;;
    *) require_command "$CXX_COMMAND" || true ;;
esac

SANITIZER_MODE="${VERIFY_SANITIZERS:-auto}"
TSAN_MODE="${VERIFY_TSAN:-auto}"
MATRIX_MODE="${VERIFY_COMPILER_MATRIX:-auto}"
STRICT_MODE="${VERIFY_STRICT:-0}"
validate_mode VERIFY_SANITIZERS "$SANITIZER_MODE" || true
validate_mode VERIFY_TSAN "$TSAN_MODE" || true
validate_mode VERIFY_COMPILER_MATRIX "$MATRIX_MODE" || true
case "$STRICT_MODE" in
    0|1) ;;
    *) log "[FAIL] VERIFY_STRICT must be 0 or 1, found: $STRICT_MODE"; FAILED=1 ;;
esac

OS_NAME="$(uname -s 2>/dev/null || true)"
case "$OS_NAME" in
    Linux) ASAN_DEFAULT='detect_leaks=1:halt_on_error=1' ;;
    Darwin)
        ASAN_DEFAULT='detect_leaks=0:halt_on_error=1'
        require_command lsof || true
        ;;
    *)
        log "[FAIL] 전체 C++98 POSIX 검증은 Linux, macOS 또는 WSL이 필요합니다: $OS_NAME"
        FAILED=1
        ASAN_DEFAULT='halt_on_error=1'
        ;;
esac

if [ "$FAILED" -ne 0 ]; then
    exit 1
fi

log "VERIFY LOG: $LOG"
log "OS: $(uname -a 2>/dev/null || true)"
log "PRIMARY CXX: $(command -v "$CXX_COMMAND")"
"$CXX_COMMAND" --version >> "$LOG" 2>&1 || true
cmake --version >> "$LOG" 2>&1 || true
python3 --version >> "$LOG" 2>&1 || true
make --version >> "$LOG" 2>&1 || true

run_check 'python-version' 30 python3 -c \
    'import sys; assert sys.version_info >= (3, 9), sys.version' || true
run_check 'cmake-version' 30 python3 -c \
    'import re,subprocess; s=subprocess.check_output(["cmake","--version"],text=True).splitlines()[0]; m=re.search(r"(\d+)\.(\d+)(?:\.(\d+))?",s); assert m and tuple(int(x or 0) for x in m.groups()) >= (3,20,0), s' || true
run_check 'all-shell-syntax' 60 bash -c \
    'find . -path ./.git -prune -o -type f -name "*.sh" -exec bash -n {} +' || true
run_check 'repository-structure' 180 python3 scripts/validate_docs.py --mode full || true
run_check 'verifier-meta-tests' 120 python3 scripts/selftest_verifiers.py || true
run_check 'git-whitespace' 60 bash -c \
    'if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git diff --check; fi' || true

if [ "$FAILED" -ne 0 ]; then
    log '구조 또는 preflight가 실패했습니다. 가능한 정리 절차를 수행합니다.'
    exit 1
fi

CONTROL_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/guide-cpp-verify-control.XXXXXX")"
WORK_ROOT="$CONTROL_ROOT/work"
mkdir -p "$WORK_ROOT"
SOURCE_BEFORE="$CONTROL_ROOT/source-before.json"
python3 scripts/manage_artifacts.py snapshot "$ROOT" > "$SOURCE_BEFORE"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT_AVAILABLE=1
    TRACKED_STATUS_BEFORE="$CONTROL_ROOT/git-tracked-before"
    git status --porcelain=v1 --untracked-files=no > "$TRACKED_STATUS_BEFORE"
fi

section 'ORIGINAL WORKTREE BASELINE'
run_check 'original-generated-artifact-clean' 90     python3 scripts/manage_artifacts.py clean "$ROOT" || true
run_check 'original-generated-artifact-audit' 90     python3 scripts/manage_artifacts.py audit "$ROOT" || true

# Build a primary compiler plus one genuinely distinct alternate compiler when
# available. Users can disable this with VERIFY_COMPILER_MATRIX=off.
COMPILER_FILE="$CONTROL_ROOT/compilers"
: > "$COMPILER_FILE"
PRIMARY_PATH="$(command -v "$CXX_COMMAND")"
printf '%s\n' "$PRIMARY_PATH" >> "$COMPILER_FILE"

if [ "$MATRIX_MODE" != 'off' ]; then
    PRIMARY_REAL="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$PRIMARY_PATH")"
    PRIMARY_VERSION="$($PRIMARY_PATH --version 2>/dev/null | head -1 || true)"
    if printf '%s' "$PRIMARY_VERSION" | grep -qi clang; then
        CANDIDATES='g++ c++ clang++'
    else
        CANDIDATES='clang++ g++ c++'
    fi
    for candidate in $CANDIDATES; do
        candidate_path="$(command -v "$candidate" 2>/dev/null || true)"
        [ -n "$candidate_path" ] || continue
        candidate_real="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$candidate_path")"
        [ "$candidate_real" != "$PRIMARY_REAL" ] || continue
        printf '%s\n' "$candidate_path" >> "$COMPILER_FILE"
        break
    done
fi

COMPILER_COUNT="$(wc -l < "$COMPILER_FILE" | tr -d ' ')"
if [ "$MATRIX_MODE" = 'off' ]; then
    skip_check 'alternate compiler matrix' 'VERIFY_COMPILER_MATRIX=off'
elif [ "$COMPILER_COUNT" -lt 2 ]; then
    if [ "$MATRIX_MODE" = 'required' ]; then
        log '[FAIL] VERIFY_COMPILER_MATRIX=required이지만 서로 다른 compiler 두 개를 찾지 못했습니다.'
        FAILED=1
    else
        skip_check 'alternate compiler matrix' '서로 다른 두 번째 compiler를 찾지 못함'
    fi
fi

index=0
while IFS= read -r compiler; do
    [ -n "$compiler" ] || continue
    index=$((index + 1))
    compiler_name="$(basename "$compiler")"
    workspace="$WORK_ROOT/${index}-${compiler_name}"
    copy_repository "$workspace"
    workspace_source_before="$CONTROL_ROOT/workspace-${index}-before.json"
    python3 "$workspace/scripts/manage_artifacts.py" snapshot "$workspace" > "$workspace_source_before"
    cd "$workspace" || exit 1

    section "COMPILER $index/$COMPILER_COUNT: $compiler"
    run_check "$compiler_name clean-start" 240 env CXX="$compiler" make clean || true
    run_check "$compiler_name python-syntax" 180 python3 -m compileall -q scripts exercises || true
    run_check "$compiler_name docs" 180 python3 scripts/validate_docs.py --mode full || true
    run_check "$compiler_name verifier-meta-tests" 120 python3 scripts/selftest_verifiers.py || true
    run_check "$compiler_name modern-start-state" 900 env CXX="$compiler" make modern-start-state || true
    run_check "$compiler_name modern-debug" 1200 env CXX="$compiler" make modern-test || true
    run_check "$compiler_name modern-release" 1200 env CXX="$compiler" make modern-release || true
    run_check "$compiler_name cpp98-skeleton-build" 1200 env CXX="$compiler" make skeleton-build || true
    run_check "$compiler_name cpp98-reference" 1800 env CXX="$compiler" make test || true
    run_check "$compiler_name cpp98-network-stress" 1200 env CXX="$compiler" \
        make -C exercises/02-cpp98-systems/networking/line-server stress || true
    run_check "$compiler_name cpp98-failure-contracts" 1800 env CXX="$compiler" make failure-check || true

    if [ "$index" -eq 1 ]; then
        case "$SANITIZER_MODE" in
            off)
                skip_check 'ASan·UBSan' 'VERIFY_SANITIZERS=off'
                ;;
            auto|required)
                if probe_sanitizer "$compiler" asan-ubsan "$workspace/.guide-probes/asan-ubsan"; then
                    run_check "$compiler_name modern-asan-ubsan" 1800 \
                        env CXX="$compiler" \
                        ASAN_OPTIONS="${ASAN_OPTIONS:-$ASAN_DEFAULT}" \
                        UBSAN_OPTIONS="${UBSAN_OPTIONS:-halt_on_error=1:print_stacktrace=1}" \
                        make modern-sanitize || true
                    run_check "$compiler_name cpp98-asan-ubsan" 2400 \
                        env CXX="$compiler" \
                        ASAN_OPTIONS="${ASAN_OPTIONS:-$ASAN_DEFAULT}" \
                        UBSAN_OPTIONS="${UBSAN_OPTIONS:-halt_on_error=1:print_stacktrace=1}" \
                        make sanitize || true
                elif [ "$SANITIZER_MODE" = 'required' ]; then
                    log '[FAIL] ASan·UBSan compiler/runtime probe가 실패했습니다.'
                    FAILED=1
                else
                    skip_check 'ASan·UBSan' '현재 compiler/runtime에서 probe 실패'
                fi
                ;;
        esac

        case "$TSAN_MODE" in
            off)
                skip_check 'ThreadSanitizer' 'VERIFY_TSAN=off'
                ;;
            auto|required)
                if probe_sanitizer "$compiler" tsan "$workspace/.guide-probes/tsan"; then
                    run_check "$compiler_name modern-thread-sanitizer" 2400 \
                        env CXX="$compiler" \
                        TSAN_OPTIONS="${TSAN_OPTIONS:-halt_on_error=1}" \
                        make modern-thread-sanitize || true
                elif [ "$TSAN_MODE" = 'required' ]; then
                    log '[FAIL] ThreadSanitizer compiler/runtime probe가 실패했습니다.'
                    FAILED=1
                else
                    skip_check 'ThreadSanitizer' '현재 compiler/runtime에서 probe 실패'
                fi
                ;;
        esac
    fi

    run_check "$compiler_name final-clean" 300 make clean || true
    run_check "$compiler_name generated-artifact-clean" 90 \
        python3 scripts/manage_artifacts.py clean "$workspace" || true
    run_check "$compiler_name generated-artifact-audit" 90 \
        python3 scripts/manage_artifacts.py audit "$workspace" || true
    workspace_source_after="$CONTROL_ROOT/workspace-${index}-after.json"
    python3 scripts/manage_artifacts.py snapshot "$workspace" > "$workspace_source_after"
    if cmp -s "$workspace_source_before" "$workspace_source_after"; then
        log "[PASS] $compiler_name build·test 뒤 workspace source snapshot 동일"
    else
        log "[FAIL] $compiler_name build·test가 workspace의 비생성 파일을 변경했습니다."
        FAILED=1
    fi
    cd "$ROOT" || exit 1
done < "$COMPILER_FILE"

section 'ORIGINAL WORKTREE INTEGRITY'
clean_workspaces

SOURCE_AFTER="$CONTROL_ROOT/source-after.json"
python3 scripts/manage_artifacts.py snapshot "$ROOT" > "$SOURCE_AFTER"
if cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
    log '[PASS] verify.sh 실행 전후 source·문서·설정 snapshot 동일'
else
    log '[FAIL] verify.sh가 원본의 비생성 파일을 변경했습니다.'
    python3 - "$SOURCE_BEFORE" "$SOURCE_AFTER" >> "$LOG" 2>&1 <<'PY'
import json
import sys

before = {item["path"]: item for item in json.load(open(sys.argv[1], encoding="utf-8"))}
after = {item["path"]: item for item in json.load(open(sys.argv[2], encoding="utf-8"))}
for path in sorted(before.keys() | after.keys()):
    if before.get(path) != after.get(path):
        print(path)
        print("  before:", before.get(path))
        print("  after: ", after.get(path))
PY
    FAILED=1
fi

if [ "$GIT_AVAILABLE" -eq 1 ]; then
    TRACKED_STATUS_AFTER="$CONTROL_ROOT/git-tracked-after"
    git status --porcelain=v1 --untracked-files=no > "$TRACKED_STATUS_AFTER"
    if cmp -s "$TRACKED_STATUS_BEFORE" "$TRACKED_STATUS_AFTER"; then
        log '[PASS] verify.sh 실행 전후 tracked Git 상태 동일'
    else
        log '[FAIL] verify.sh가 tracked Git 상태를 변경했습니다.'
        {
            printf '%s\n' '--- before'
            cat "$TRACKED_STATUS_BEFORE"
            printf '%s\n' '--- after'
            cat "$TRACKED_STATUS_AFTER"
        } >> "$LOG"
        FAILED=1
    fi
    run_check 'final-git-whitespace' 60 git diff --check || true
fi

if [ "$STRICT_MODE" -eq 1 ] && [ "$SKIPPED" -ne 0 ]; then
    log "[FAIL] VERIFY_STRICT=1인데 $SKIPPED개 검사가 건너뛰어졌습니다."
    FAILED=1
fi

cleanup_all
trap - EXIT HUP INT TERM

section 'RESULT'
if [ "$FAILED" -eq 0 ]; then
    log "RESULT: PASS (skipped=$SKIPPED)"
    log "VERIFY LOG: $LOG"
    exit 0
fi

log "RESULT: FAIL (skipped=$SKIPPED)"
log "VERIFY LOG: $LOG"
exit 1
