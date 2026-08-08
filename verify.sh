#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="git"
STATE_TOOL="$ROOT/scripts/repository_state.py"
MARKER="$ROOT/.guide/$GUIDE_ID/prepared.json"
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
    GUIDE_INDEX="$index" GUIDE_HEAD="$head" GUIDE_GIT="$(git --version)" \
    GUIDE_PYTHON="$(python3 --version 2>&1)" GUIDE_BASH="$BASH_VERSION" \
    GUIDE_MAKE="$(make --version 2>&1)" GUIDE_MKTEMP="$(command -v mktemp)" python3 - <<'PY'
import json, os, platform, sys
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
    },
}
for key, value in expected.items():
    if data.get(key) != value:
        raise SystemExit(f"stale prepared marker field: {key}")
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

check_clean_preservation() {
    local repository="$WORK/git-clean-repository"
    copy_source "$repository"
    mkdir -p -- "$repository/exercises/workspace" "$repository/.guide/git"
    printf 'learner workspace\n' > "$repository/exercises/workspace/sentinel"
    printf 'prepared state\n' > "$repository/.guide/git/sentinel"
    make -C "$repository" --no-print-directory clean >/dev/null
    [[ "$(cat "$repository/exercises/workspace/sentinel")" == 'learner workspace' ]] || \
        die 'make clean이 Git learner workspace를 변경했습니다.'
    [[ "$(cat "$repository/.guide/git/sentinel")" == 'prepared state' ]] || \
        die 'make clean이 Git 준비 상태를 변경했습니다.'
}

if [[ "${GUIDE_VERIFY_TEST_HOLD:-0}" == 1 ]]; then
    run 'top-level signal cleanup fixture' signal_cleanup_fixture
fi
run 'fresh prepared marker' check_marker
ORIGINAL_SOURCE="$(python3 "$STATE_TOOL" fingerprint --root "$ROOT")"
ORIGINAL_INDEX="$(python3 "$STATE_TOOL" index --root "$ROOT")"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/guide-git-verify.XXXXXX")"
COPY="$WORK/repository"
copy_source "$COPY"
COPY_BEFORE="$(python3 "$COPY/scripts/repository_state.py" fingerprint --root "$COPY")"
export PYTHONDONTWRITEBYTECODE=1
export GIT_CONFIG_GLOBAL="$WORK/global.gitconfig"
export GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0 GIT_PAGER=cat PAGER=cat GIT_EDITOR=true
: > "$GIT_CONFIG_GLOBAL"

run 'exact layout, links, pedagogy and shell fences' python3 -B "$COPY/scripts/validate.py"
run 'fifteen layout-validator mutants' python3 -B "$COPY/scripts/test-validator.py"
run 'shell entrypoint syntax' bash -n "$COPY/prepare.sh" "$COPY/verify.sh" \
    "$COPY/exercises/setup.sh" "$COPY/scripts/test-prepare-safety.sh" \
    "$COPY/scripts/validate.sh"
run 'atomic prepared-marker safety' "$COPY/scripts/test-prepare-safety.sh"
run 'hermetic local Git scenarios' bash -c 'cd "$1" && ./scripts/validate.sh' _ "$COPY"
run 'clean preserves learner and prepared state' check_clean_preservation

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
