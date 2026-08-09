#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="data-engineering"
STATE_TOOL="$ROOT/scripts/repository_state.py"
MARKER="$ROOT/.guide/$GUIDE_ID/prepared.json"
EXPECTED_STEPS=12
PASS_COUNT=0
FAIL_COUNT=0
SUCCESS=0
SUMMARY_EMITTED=0
LOG=''
LOG_ACTIVE=0
LOG_ID=''
WORK=''
COPY=''
ACTIVE_PID=''
ORIGINAL_SOURCE=''
ORIGINAL_WORKSPACE=''
ORIGINAL_INDEX=''
ORIGINAL_HEAD=''
export GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1
exec 3>&1 4>&2

skipped_count() {
    local value=$((EXPECTED_STEPS - PASS_COUNT - FAIL_COUNT))
    (( value >= 0 )) || value=0
    printf '%s' "$value"
}

write_summary() {
    local result=$1
    local skipped
    skipped="$(skipped_count)"
    if (( LOG_ACTIVE == 1 )); then
        printf 'passed=%d failed=%d skipped=%s\n' "$PASS_COUNT" "$FAIL_COUNT" "$skipped" >&5
        printf 'VERIFY LOG: %s\nRESULT: %s\n' "$LOG" "$result" >&5
    fi
    printf 'passed=%d failed=%d skipped=%s\n' "$PASS_COUNT" "$FAIL_COUNT" "$skipped" >&3
    printf 'VERIFY LOG: %s\nRESULT: %s\n' "${LOG:-unavailable}" "$result" >&3
    SUMMARY_EMITTED=1
}

preflight_die() {
    local message=$*
    (( FAIL_COUNT > 0 )) || FAIL_COUNT=1
    if (( LOG_ACTIVE == 1 )); then
        printf '[verify] ERROR: %s\n' "$message" >&5
    fi
    printf '[verify] ERROR: %s\n' "$message" >&4
    write_summary FAIL
    exit 2
}

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

preservation_ok() {
    [[ -n "$ORIGINAL_SOURCE" ]] || return 0
    local failed=0
    [[ "$ORIGINAL_SOURCE" == "$(python3 -B "$STATE_TOOL" source --root "$ROOT")" ]] || {
        printf '[verify] ERROR: 원본 source tree가 변경됐습니다.\n' >&5
        failed=1
    }
    [[ "$ORIGINAL_WORKSPACE" == "$(python3 -B "$STATE_TOOL" workspace --root "$ROOT")" ]] || {
        printf '[verify] ERROR: 학습자 workspace가 변경됐습니다.\n' >&5
        failed=1
    }
    [[ "$ORIGINAL_INDEX" == "$(python3 -B "$STATE_TOOL" index --root "$ROOT")" ]] || {
        printf '[verify] ERROR: Git index가 변경됐습니다.\n' >&5
        failed=1
    }
    [[ "$ORIGINAL_HEAD" == "$(git -C "$ROOT" rev-parse --verify HEAD)" ]] || {
        printf '[verify] ERROR: HEAD가 변경됐습니다.\n' >&5
        failed=1
    }
    return "$failed"
}

finish() {
    local status=$?
    trap - EXIT HUP INT TERM
    terminate_active
    if ! preservation_ok; then
        (( FAIL_COUNT += 1 ))
        status=1
    fi
    if [[ -n "$WORK" && -d "$WORK" && ! -L "$WORK" ]]; then
        rm -rf -- "$WORK"
    fi
    if (( status != 0 || SUCCESS != 1 )); then
        (( FAIL_COUNT > 0 )) || FAIL_COUNT=1
        (( SUMMARY_EMITTED == 1 )) || write_summary FAIL
        (( status != 0 )) || status=1
    fi
    exit "$status"
}
trap finish EXIT
trap 'terminate_active; exit 129' HUP
trap 'terminate_active; exit 130' INT
trap 'terminate_active; exit 143' TERM

for command_name in bash git make mktemp python3; do
    command -v "$command_name" >/dev/null 2>&1 || preflight_die "필수 명령이 없습니다: $command_name"
done
python3 - <<'PY' || preflight_die 'Python 3.11 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY

umask 077
if [[ -n "${VERIFY_LOG:-}" ]]; then
    requested_log="$VERIFY_LOG"
else
    log_parent="$(mktemp -d "${TMPDIR:-/tmp}/guide-data-engineering-log.XXXXXX")" || \
        preflight_die '기본 verify log 디렉터리를 만들지 못했습니다.'
    log_parent_real="$(cd -- "$log_parent" && pwd -P)"
    case "$log_parent_real" in
        "$ROOT"|"$ROOT"/*)
            rmdir -- "$log_parent"
            preflight_die '기본 verify log 디렉터리가 저장소 안에 생성됐습니다.'
            ;;
    esac
    requested_log="$log_parent/verify.log"
fi
LOG="$(python3 - "$ROOT" "$requested_log" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
raw = Path(sys.argv[2])
if not raw.is_absolute():
    raise SystemExit("VERIFY_LOG는 절대 경로여야 합니다.")
if os.path.lexists(raw):
    raise SystemExit("VERIFY_LOG 기존 경로를 덮어쓰지 않습니다.")
try:
    parent = raw.parent.resolve(strict=True)
except FileNotFoundError:
    raise SystemExit("VERIFY_LOG 상위 디렉터리가 존재해야 합니다.")
if not parent.is_dir():
    raise SystemExit("VERIFY_LOG 상위 경로가 디렉터리가 아닙니다.")
resolved = parent / raw.name
try:
    resolved.relative_to(root)
except ValueError:
    pass
else:
    raise SystemExit("VERIFY_LOG는 저장소 밖 경로여야 합니다.")
if os.path.lexists(resolved):
    raise SystemExit("VERIFY_LOG canonical 경로가 이미 존재합니다.")
print(resolved)
PY
)" || preflight_die '안전한 verify log 경로를 만들 수 없습니다.'
set -C
if ! exec 5>"$LOG"; then
    set +C
    preflight_die 'VERIFY_LOG를 배타적으로 만들지 못했습니다.'
fi
set +C
LOG_ACTIVE=1
LOG_ID="$(python3 - "$LOG" 5<&5 <<'PY'
import os
import stat
import sys

path_state = os.lstat(sys.argv[1])
write_state = os.fstat(5)
if (
    not stat.S_ISREG(write_state.st_mode)
    or write_state.st_nlink != 1
    or (path_state.st_dev, path_state.st_ino)
    != (write_state.st_dev, write_state.st_ino)
):
    raise SystemExit("verify log identity가 안전하지 않습니다.")
os.fchmod(5, 0o600)
print(f"{write_state.st_dev}:{write_state.st_ino}")
PY
)" || preflight_die 'VERIFY_LOG identity를 고정하지 못했습니다.'
printf '[verify] log identity: %s\n' "$LOG_ID" >&5

[[ "$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null)" == "$ROOT" ]] || \
    preflight_die '독립 Git 저장소 루트에서 실행해야 합니다.'
[[ -e "$MARKER" && ! -L "$MARKER" && -f "$MARKER" ]] || \
    preflight_die 'prepared marker가 없습니다. 먼저 ./prepare.sh를 실행하십시오.'

current_source="$(python3 -B "$STATE_TOOL" source --root "$ROOT")" || preflight_die 'source fingerprint를 읽지 못했습니다.'
current_index="$(python3 -B "$STATE_TOOL" index --root "$ROOT")" || preflight_die 'Git index fingerprint를 읽지 못했습니다.'
current_head="$(git -C "$ROOT" rev-parse --verify HEAD)" || preflight_die 'HEAD를 읽지 못했습니다.'
python_id="$(python3 - <<'PY'
import platform
import sys
print(f"{platform.python_implementation()} {platform.python_version()} ({sys.executable})")
PY
)"
make_version="$(make --version 2>&1 | sed -n '1p')"
GUIDE_MARKER="$MARKER" GUIDE_ID="$GUIDE_ID" GUIDE_HEAD="$current_head" \
GUIDE_SOURCE="$current_source" GUIDE_INDEX="$current_index" GUIDE_PYTHON="$python_id" \
GUIDE_GIT="$(git --version)" GUIDE_MAKE="$make_version" GUIDE_MKTEMP="$(command -v mktemp)" \
GUIDE_BASH="$BASH_VERSION" python3 - <<'PY' || preflight_die 'prepare marker가 현재 저장소/도구 상태와 다릅니다.'
import json
import os
import stat
from pathlib import Path

path = Path(os.environ["GUIDE_MARKER"])
metadata = path.lstat()
if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
    raise SystemExit("prepared marker는 단일 일반 파일이어야 합니다.")
if stat.S_IMODE(metadata.st_mode) != 0o600:
    raise SystemExit("prepared marker mode는 0600이어야 합니다.")
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"invalid prepared marker: {exc}")
expected = {
    "schema_version": 2,
    "guide_id": os.environ["GUIDE_ID"],
    "head_commit": os.environ["GUIDE_HEAD"],
    "source_fingerprint": os.environ["GUIDE_SOURCE"],
    "index_fingerprint": os.environ["GUIDE_INDEX"],
    "tools": {
        "bash": os.environ["GUIDE_BASH"],
        "git": os.environ["GUIDE_GIT"],
        "make": os.environ["GUIDE_MAKE"],
        "mktemp": os.environ["GUIDE_MKTEMP"],
        "python": os.environ["GUIDE_PYTHON"],
    },
}
if payload != expected:
    differing = sorted(key for key in set(payload) | set(expected) if payload.get(key) != expected.get(key))
    raise SystemExit("stale prepared marker fields: " + ", ".join(differing))
PY

ORIGINAL_SOURCE="$current_source"
ORIGINAL_WORKSPACE="$(python3 -B "$STATE_TOOL" workspace --root "$ROOT")"
ORIGINAL_INDEX="$current_index"
ORIGINAL_HEAD="$current_head"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/guide-data-engineering-work.XXXXXX")" || \
    preflight_die '격리 검증 디렉터리를 만들지 못했습니다.'
work_real="$(cd -- "$WORK" && pwd -P)"
case "$work_real" in "$ROOT"|"$ROOT"/*) preflight_die '검증 임시 디렉터리가 저장소 안에 있습니다.' ;; esac
[[ -d "$WORK" && ! -L "$WORK" ]] || preflight_die '검증 임시 경로가 실제 디렉터리가 아닙니다.'
COPY="$WORK/repository"
python3 - "$ROOT" "$COPY" <<'PY' || preflight_die '격리 source 복사에 실패했습니다.'
import os
import shutil
import sys
from pathlib import Path

source, target = map(Path, sys.argv[1:])

def ignore(directory: str, names: list[str]) -> set[str]:
    current = Path(directory)
    relative = current.relative_to(source)
    ignored: set[str] = set()
    for name in names:
        candidate = relative / name
        if not candidate.parts:
            continue
        if candidate.parts[0] in {".git", ".guide"}:
            ignored.add(name)
        elif name in {".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv", "__pycache__", "htmlcov"}:
            ignored.add(name)
        elif name in {".coverage", ".DS_Store"} or Path(name).suffix in {".pyc", ".pyo"}:
            ignored.add(name)
        elif candidate.parts[0] == "exercises" and "workspace" in candidate.parts[1:]:
            ignored.add(name)
    return ignored

shutil.copytree(source, target, symlinks=True, ignore=ignore)
PY
copy_before="$(python3 -B "$COPY/scripts/repository_state.py" source --root "$COPY")"
if [[ "${GUIDE_VERIFY_TEST_FAIL_AFTER_COPY:-0}" == 1 ]]; then
    printf '[verify] induced failure after isolated copy\n' >&5
    exit 97
fi
cd "$COPY"

run_step() {
    local label=$1
    local status
    shift
    printf '\n==> %s\n' "$label" >&5
    set -m
    "$@" >&5 2>&1 &
    ACTIVE_PID=$!
    set +m
    if wait "$ACTIVE_PID"; then
        status=0
    else
        status=$?
    fi
    ACTIVE_PID=''
    if (( status == 0 )); then
        (( PASS_COUNT += 1 ))
        printf 'PASS %s\n' "$label" >&5
    else
        (( FAIL_COUNT += 1 ))
        printf 'FAIL %s (status=%d)\n' "$label" "$status" >&5
    fi
}

check_stability() {
    local copy_after
    copy_after="$(python3 -B "$COPY/scripts/repository_state.py" source --root "$COPY")"
    [[ "$copy_before" == "$copy_after" ]] || return 1
    preservation_ok
}

run_step 'repository structure, links and contracts' python3 -B scripts/validate.py
run_step 'repository-state regressions' python3 -B scripts/test_repository_state.py
run_step 'validator mutant regressions' python3 -B scripts/test_validator.py
run_step 'atomic prepared-marker safety' python3 -B scripts/test_prepare_safety.py
run_step 'verify log/preflight safety' python3 -B scripts/test_verify_preflight.py
run_step 'precise clean preservation' python3 -B scripts/test_clean_safety.py
run_step 'workspace no-overwrite and cleanup safety' python3 -B scripts/test_workspace_tools.py
run_step 'shell entrypoint syntax' bash -n prepare.sh verify.sh scripts/new-workspace.sh scripts/check-workspace.sh
run_step 'example unit tests' python3 -B -m unittest discover -s tests -p 'test_*.py' -v
run_step 'starter/reference/known-wrong contracts' python3 -B scripts/exercise_tool.py verify-all
run_step 'example smoke' python3 -B examples/schema_compatibility.py
run_step 'source, workspace, index and isolated-copy stability' check_stability

if (( FAIL_COUNT != 0 || PASS_COUNT != EXPECTED_STEPS )); then
    write_summary FAIL
    exit 1
fi
python3 - "$LOG" 5<&5 <<'PY'
import os
import stat
import sys

path_state = os.lstat(sys.argv[1])
write_state = os.fstat(5)
if (path_state.st_dev, path_state.st_ino) != (write_state.st_dev, write_state.st_ino):
    raise SystemExit("verify log path identity changed")
if not stat.S_ISREG(write_state.st_mode):
    raise SystemExit("verify log is no longer regular")
PY
SUCCESS=1
printf '\nVERIFY OK: 모든 필수 검사가 실행됐으며 자동 검사는 인간 rubric 검토를 대체하지 않습니다.\n' >&5
printf '\nVERIFY OK: 모든 필수 검사가 실행됐으며 자동 검사는 인간 rubric 검토를 대체하지 않습니다.\n' >&3
write_summary PASS
