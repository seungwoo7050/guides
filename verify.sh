#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="python"
STATE_TOOL="$ROOT/scripts/repository_state.py"
MARKER="$ROOT/.guide/$GUIDE_ID/prepared.json"
VENV="$ROOT/.guide/$GUIDE_ID/venv"
PYTHON="$VENV/bin/python"
PASS_COUNT=0
SUCCESS=0
WORK=''
LOG=''
LOG_DISPLAY='unavailable'
LOG_ACTIVE=0
ACTIVE_PID=''
export GIT_OPTIONAL_LOCKS=0
exec 3>&1 4>&2

die() { printf '[verify] ERROR: %s\n' "$*" >&2; exit 1; }
terminate_active() {
    local pid="${ACTIVE_PID:-}"
    [[ -n "$pid" ]] || return 0
    if kill -0 "$pid" 2>/dev/null; then
        kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
        for _ in {1..50}; do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.02
        done
        if kill -0 "$pid" 2>/dev/null; then
            kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
        fi
    fi
    wait "$pid" 2>/dev/null || true
    ACTIVE_PID=''
}
finish() {
    local status=$?
    trap - EXIT HUP INT TERM
    terminate_active
    [[ -z "$WORK" || ! -d "$WORK" ]] || rm -rf -- "$WORK"
    if (( status != 0 || SUCCESS != 1 )); then
        if (( LOG_ACTIVE == 1 )); then
            printf 'passed=%s failed=1 skipped=0\n' "$PASS_COUNT" >&2
            printf 'VERIFY LOG: %s\nRESULT: FAIL\n' "$LOG_DISPLAY" >&2
        fi
        printf 'passed=%s failed=1 skipped=0\n' "$PASS_COUNT" >&4
        printf 'VERIFY LOG: %s\nRESULT: FAIL\n' "$LOG_DISPLAY" >&4
        (( status != 0 )) || status=1
    fi
    exit "$status"
}
trap finish EXIT
trap 'terminate_active; exit 129' HUP
trap 'terminate_active; exit 130' INT
trap 'terminate_active; exit 143' TERM

[[ "$#" -le 1 ]] || die '사용법: ./verify.sh [/absolute/external/log]'
[[ "$(pwd -P)" == "$ROOT" ]] || die '저장소 루트에서 ./verify.sh를 실행하십시오.'
for command_name in git bash python3 mktemp make; do
    command -v "$command_name" >/dev/null 2>&1 || die "필수 명령이 없습니다: $command_name"
done
python3 - <<'PY' || die 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

LOG="${1:-${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-$GUIDE_ID-verify-$$.log}}"
LOG_DISPLAY="$LOG"
[[ "$LOG" == /* ]] || die 'verify log는 절대 경로여야 합니다.'
[[ ! -L "$LOG" ]] || die 'verify log symlink를 허용하지 않습니다.'
LOG="$(python3 - "$LOG" <<'PY'
import sys
from pathlib import Path
print(Path(sys.argv[1]).resolve())
PY
)"
LOG_DISPLAY="$LOG"
case "$LOG" in "$ROOT"|"$ROOT"/*) die 'verify log는 저장소 밖에 있어야 합니다.' ;; esac
[[ -d "$(dirname -- "$LOG")" ]] || die 'verify log의 상위 디렉터리가 없습니다.'
[[ ! -d "$LOG" ]] || die 'verify log 경로가 디렉터리입니다.'
: > "$LOG"
exec > "$LOG" 2>&1
LOG_ACTIVE=1

run() {
    local label=$1
    local status
    shift
    printf '\n==> %s\n' "$label"
    set -m
    "$@" &
    ACTIVE_PID=$!
    set +m
    if wait "$ACTIVE_PID"; then
        status=0
    else
        status=$?
    fi
    ACTIVE_PID=''
    (( status == 0 )) || return "$status"
    PASS_COUNT=$((PASS_COUNT + 1))
    printf 'PASS  %s\n' "$label"
}

signal_cleanup_fixture() {
    local pid_file="${GUIDE_VERIFY_TEST_PID_FILE:-}"
    [[ "$pid_file" == /* ]] || die 'signal cleanup fixture PID file은 절대 경로여야 합니다.'
    [[ ! -e "$pid_file" && ! -L "$pid_file" ]] || die 'signal cleanup fixture PID file이 이미 있습니다.'
    GUIDE_VERIFY_TEST_PID_FILE="$pid_file" bash -c '
        printf "%s\n" "$$" > "$GUIDE_VERIFY_TEST_PID_FILE"
        exec sleep 300
    '
}

check_marker() {
    [[ -f "$MARKER" ]] || die 'prepared marker가 없습니다. 먼저 ./prepare.sh를 실행하십시오.'
    [[ -x "$PYTHON" ]] || die '.guide/python/venv가 없습니다. 먼저 ./prepare.sh를 실행하십시오.'
    local source index head raw_index_path raw_index
    source="$(python3 "$STATE_TOOL" fingerprint --root "$ROOT")"
    index="$(python3 "$STATE_TOOL" index --root "$ROOT")"
    raw_index_path="$(git -C "$ROOT" rev-parse --path-format=absolute --git-path index)"
    raw_index="$(python3 - "$raw_index_path" <<'PY'
import hashlib, sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
    [[ "$index" == "$raw_index" ]] || die 'Git index fingerprint가 raw index bytes와 다릅니다.'
    head="$(git -C "$ROOT" rev-parse HEAD)"
    GUIDE_MARKER="$MARKER" GUIDE_EXPECTED_ID="$GUIDE_ID" GUIDE_SOURCE="$source" \
    GUIDE_INDEX="$index" GUIDE_HEAD="$head" GUIDE_VENV="$VENV" \
    GUIDE_GIT="$(git --version)" GUIDE_PYTHON="$(python3 --version 2>&1)" \
    GUIDE_VENV_PYTHON="$("$PYTHON" --version 2>&1)" GUIDE_BASH="$BASH_VERSION" \
    GUIDE_MAKE="$(make --version 2>&1)" GUIDE_MKTEMP="$(command -v mktemp)" \
    "$PYTHON" -B - <<'PY'
import json, os, platform
from pathlib import Path
path = Path(os.environ["GUIDE_MARKER"])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid prepared marker: {exc}")
expected = {
    "schema": 3,
    "guide_id": os.environ["GUIDE_EXPECTED_ID"],
    "head": os.environ["GUIDE_HEAD"],
    "source_fingerprint": os.environ["GUIDE_SOURCE"],
    "index_fingerprint": os.environ["GUIDE_INDEX"],
    "venv": os.environ["GUIDE_VENV"],
    "platform": {
        "machine": platform.machine(),
        "platform": platform.platform(),
        "python_implementation": platform.python_implementation(),
        "system": platform.system(),
    },
    "tools": {
        "bash": os.environ["GUIDE_BASH"],
        "git": os.environ["GUIDE_GIT"],
        "make": os.environ["GUIDE_MAKE"],
        "mktemp": os.environ["GUIDE_MKTEMP"],
        "python": os.environ["GUIDE_PYTHON"],
        "venv_python": os.environ["GUIDE_VENV_PYTHON"],
    },
}
for key, value in expected.items():
    if data.get(key) != value:
        raise SystemExit(f"stale prepared marker field: {key}")
PY
    "$PYTHON" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
}

copy_source() {
    python3 - "$ROOT" "$1" <<'PY'
import shutil, sys
from pathlib import Path
source, target = map(Path, sys.argv[1:])
shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns(
    ".git", ".guide", ".venv", ".pytest_cache", "__pycache__", "workspace", "*.pyc", "*.pyo", "*.log"))
PY
}

check_workspace_safety() {
    local repository="$WORK/python-workspace-repository"
    local exercise
    local script
    local external="$WORK/python-external"
    local hold_pid
    copy_source "$repository"
    exercise="$repository/exercises/command-checker"
    script="$repository/scripts/new-workspace.sh"
    mkdir -p -- "$external/skeleton" "$repository/unused"
    printf 'preserve\n' > "$external/sentinel"

    if "$script" "$external" >/dev/null 2>&1; then
        die '임의의 외부 exercise 경로를 허용했습니다.'
    fi
    if "$script" "$repository/unused/../exercises/command-checker" >/dev/null 2>&1; then
        die '경로 순회 표기를 허용했습니다.'
    fi

    mv -- "$exercise/skeleton" "$exercise/skeleton.real"
    ln -s -- "$external/skeleton" "$exercise/skeleton"
    if "$script" "$exercise" >/dev/null 2>&1; then
        die 'skeleton symlink를 복사했습니다.'
    fi
    rm -- "$exercise/skeleton"
    mv -- "$exercise/skeleton.real" "$exercise/skeleton"

    ln -s -- "$external/missing" "$exercise/workspace"
    if "$script" "$exercise" >/dev/null 2>&1; then
        die 'workspace symlink를 거부하지 않았습니다.'
    fi
    rm -- "$exercise/workspace"

    GUIDE_WORKSPACE_TEST_HOLD=1 GUIDE_WORKSPACE_TEST_READY_FILE="$WORK/python-workspace-ready" \
        "$script" "$exercise" >"$WORK/python-workspace-hold.log" 2>&1 &
    hold_pid=$!
    for _ in {1..100}; do
        [[ -d "$exercise/.workspace.lock" && -s "$WORK/python-workspace-ready" ]] && break
        kill -0 "$hold_pid" 2>/dev/null || break
        sleep 0.02
    done
    [[ -d "$exercise/.workspace.lock" && -s "$WORK/python-workspace-ready" ]] || \
        die '완성된 Python staging과 동시성 lock을 관찰하지 못했습니다.'
    if "$script" "$exercise" >/dev/null 2>&1; then
        kill -TERM "$hold_pid" 2>/dev/null || true
        wait "$hold_pid" 2>/dev/null || true
        die '동시 workspace 생성이 lock을 우회했습니다.'
    fi
    kill -TERM "$hold_pid"
    if wait "$hold_pid" 2>/dev/null; then
        die '중단된 workspace 생성이 성공 상태를 반환했습니다.'
    fi
    [[ ! -e "$exercise/.workspace.lock" && ! -e "$exercise/workspace" ]]
    [[ -z "$(find "$exercise" -maxdepth 1 -name '.workspace.tmp.*' -print -quit)" ]] || \
        die '중단 뒤 workspace 임시 디렉터리가 남았습니다.'

    GUIDE_WORKSPACE_TEST_HOLD=1 GUIDE_WORKSPACE_TEST_READY_FILE="$WORK/python-race-ready" \
        GUIDE_WORKSPACE_TEST_RELEASE_FILE="$WORK/python-race-release" \
        "$script" "$exercise" >"$WORK/python-workspace-race.log" 2>&1 &
    hold_pid=$!
    for _ in {1..200}; do
        [[ -s "$WORK/python-race-ready" ]] && break
        kill -0 "$hold_pid" 2>/dev/null || break
        sleep 0.02
    done
    [[ -s "$WORK/python-race-ready" ]] || die 'Python destination race fixture가 준비되지 않았습니다.'
    mkdir -- "$exercise/workspace"
    printf 'racing destination\n' > "$exercise/workspace/sentinel"
    touch "$WORK/python-race-release"
    if wait "$hold_pid" 2>/dev/null; then
        die 'Python exclusive publish가 경쟁 destination을 덮어썼습니다.'
    fi
    [[ "$(cat "$exercise/workspace/sentinel")" == 'racing destination' ]]
    [[ ! -e "$exercise/.workspace.lock" ]]
    [[ -z "$(find "$exercise" -maxdepth 1 -name '.workspace.tmp.*' -print -quit)" ]]
    rm -rf -- "$exercise/workspace"

    "$script" "$exercise" >/dev/null
    [[ -f "$exercise/workspace/command_checker/cli.py" ]]
    printf 'learner work\n' > "$exercise/workspace/sentinel"
    if "$script" "$exercise" >/dev/null 2>&1; then
        die '기존 Python workspace를 덮어쓸 수 있습니다.'
    fi
    [[ -f "$exercise/workspace/sentinel" && -f "$external/sentinel" ]]
}

check_make_and_clean_contract() {
    local repository="$WORK/python-make-repository"
    local exercise="$repository/exercises/command-checker"
    copy_source "$repository"
    make -C "$repository" --no-print-directory check PYTHON="$PYTHON"
    [[ -z "$(find "$repository" \( -path "$repository/.git" -o -path "$repository/.guide" -o -path "$repository/.venv" \) -prune -o \
        \( -type d -name __pycache__ -o -type f \( -name '*.pyc' -o -name '*.pyo' \) \) -print -quit)" ]] || \
        die 'make check이 Python source cache를 만들었습니다.'
    mkdir -p -- "$exercise/workspace" "$repository/.guide/python"
    printf 'generated workspace\n' > "$exercise/workspace/sentinel"
    printf 'generated state\n' > "$repository/.guide/python/sentinel"
    printf 'preserve skeleton\n' > "$exercise/skeleton/.clean-preserve"
    make -C "$repository" --no-print-directory clean
    [[ ! -e "$exercise/workspace" && ! -L "$exercise/workspace" ]] || \
        die 'make clean이 Python workspace를 prune하지 않았습니다.'
    [[ ! -e "$repository/.guide" && ! -L "$repository/.guide" ]] || \
        die 'make clean이 Python .guide를 prune하지 않았습니다.'
    [[ "$(cat "$exercise/skeleton/.clean-preserve")" == 'preserve skeleton' ]] || \
        die 'make clean이 Python skeleton source를 변경했습니다.'
}

if [[ "${GUIDE_VERIFY_TEST_HOLD:-0}" == 1 ]]; then
    run 'top-level signal cleanup fixture' signal_cleanup_fixture
fi
run 'fresh prepared marker and Python 3.12 venv' check_marker
ORIGINAL_SOURCE="$(python3 "$STATE_TOOL" fingerprint --root "$ROOT")"
ORIGINAL_INDEX="$(python3 "$STATE_TOOL" index --root "$ROOT")"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/guide-python-verify.XXXXXX")"
COPY="$WORK/repository"
copy_source "$COPY"
COPY_BEFORE="$(python3 "$COPY/scripts/repository_state.py" fingerprint --root "$COPY")"
export PYTHONDONTWRITEBYTECODE=1

run 'exact layout, links and pedagogy' "$PYTHON" -B "$COPY/scripts/validate.py"
run 'fifteen layout-validator mutants' "$PYTHON" -B "$COPY/scripts/test-validator.py"
run 'documentation contracts' "$PYTHON" -B "$COPY/scripts/check_docs.py"
run 'shell entrypoint syntax' sh -n "$COPY/prepare.sh" "$COPY/verify.sh" \
    "$COPY/scripts/new-workspace.sh" "$COPY/scripts/test-prepare-safety.sh"
run 'atomic prepared-marker safety' "$COPY/scripts/test-prepare-safety.sh"
run 'eight skeleton stage failure contracts' bash -c 'cd "$1" && "$2" -B scripts/check_stage_contracts.py' _ "$COPY" "$PYTHON"
run 'nine reference test modules' bash -c 'cd "$1" && EXERCISE_IMPL=reference "$2" -B -m unittest discover -s exercises/command-checker/tests -p "test_*.py" -v' _ "$COPY" "$PYTHON"
run 'five code mutants' bash -c 'cd "$1" && "$2" -B scripts/check_test_quality.py' _ "$COPY" "$PYTHON"
run 'atomic workspace safety' check_workspace_safety
run 'make check cache-free and clean pruning/preservation' check_make_and_clean_contract

run 'no source Python cache after tests' "$PYTHON" -B "$COPY/scripts/validate.py"
COPY_AFTER="$(python3 "$COPY/scripts/repository_state.py" fingerprint --root "$COPY")"
[[ "$COPY_BEFORE" == "$COPY_AFTER" ]] || die '격리 검증이 복제 source의 내용·모드·symlink 상태를 바꿨습니다.'
[[ "$ORIGINAL_SOURCE" == "$(python3 "$STATE_TOOL" fingerprint --root "$ROOT")" ]] || \
    die 'verify가 원본 source tree를 변경했습니다.'
[[ "$ORIGINAL_INDEX" == "$(python3 "$STATE_TOOL" index --root "$ROOT")" ]] || \
    die 'verify가 Git index를 변경했습니다.'
PASS_COUNT=$((PASS_COUNT + 1))
printf 'PASS  source/index/mode/symlink stability\n'

SUCCESS=1
printf '\nVerification summary\n'
printf 'passed=%s failed=0 skipped=0\n' "$PASS_COUNT"
printf 'VERIFY LOG: %s\n' "$LOG"
printf 'RESULT: PASS\n'
printf 'passed=%s failed=0 skipped=0\n' "$PASS_COUNT" >&3
printf 'VERIFY LOG: %s\n' "$LOG" >&3
printf 'RESULT: PASS\n' >&3
