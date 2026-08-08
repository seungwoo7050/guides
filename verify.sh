#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_OPTIONAL_LOCKS=0
IFS=$'\n\t'

GUIDE_ID="computer-architecture"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_FILE="$ROOT/.guide/$GUIDE_ID/prepared.json"
RUN_DIR=""
PASS_COUNT=0
FAIL_COUNT=0
PREFLIGHT_FAILED=0
LOG_READY=0
STEP_PID=""
VERIFY_LOG="${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-computer-architecture-verify-$$.log}"

preflight_die() {
    PREFLIGHT_FAILED=1
    FAIL_COUNT=1
    printf '[verify] ERROR: %s\n' "$*" >&2
    printf 'passed=0 failed=1 skipped=0\n' >&2
    printf 'VERIFY LOG: %s\n' "$VERIFY_LOG" >&2
    printf 'RESULT: FAIL\n' >&2
    exit 2
}

for command in git python3 make cc bash rsync sed; do
    command -v "$command" >/dev/null 2>&1 || preflight_die "$command 명령이 필요합니다."
done
python3 - <<'PY' || preflight_die "Python 3.12 이상이 필요합니다."
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

[[ "$VERIFY_LOG" == /* ]] || preflight_die "VERIFY_LOG는 절대 경로여야 합니다: $VERIFY_LOG"
[[ ! -L "$VERIFY_LOG" ]] || preflight_die "VERIFY_LOG symlink는 허용하지 않습니다: $VERIFY_LOG"
canonical_log="$(python3 - "$ROOT" "$VERIFY_LOG" <<'PY'
import os
import sys
root = os.path.realpath(sys.argv[1])
log = os.path.realpath(sys.argv[2])
if log == root or log.startswith(root + os.sep):
    raise SystemExit(1)
print(log)
PY
)" || preflight_die "VERIFY_LOG는 저장소 밖이어야 합니다."
VERIFY_LOG="$canonical_log"
[[ -d "$(dirname "$VERIFY_LOG")" && -w "$(dirname "$VERIFY_LOG")" ]] \
    || preflight_die "VERIFY_LOG 디렉터리에 쓸 수 없습니다."
: > "$VERIFY_LOG"
exec 3>&1 4>&2
exec >> "$VERIFY_LOG" 2>&1
LOG_READY=1

log() { printf '[verify] %s\n' "$*"; }

stop_on_signal() {
    local code="$1"
    trap - HUP INT TERM
    if [[ -n "$STEP_PID" ]]; then
        kill -TERM "$STEP_PID" >/dev/null 2>&1 || true
        wait "$STEP_PID" >/dev/null 2>&1 || true
        STEP_PID=""
    fi
    exit "$code"
}

cleanup() {
    local status=$?
    trap - EXIT INT TERM HUP
    for child in $(jobs -pr 2>/dev/null); do kill "$child" >/dev/null 2>&1 || true; done
    [[ -z "$RUN_DIR" ]] || rm -rf -- "$RUN_DIR"
    if [[ $PREFLIGHT_FAILED -eq 0 ]]; then
        if [[ $status -ne 0 && $FAIL_COUNT -eq 0 ]]; then
            FAIL_COUNT=1
        fi
        if [[ $status -eq 0 && $FAIL_COUNT -ne 0 ]]; then
            status=1
        fi
        printf 'passed=%d failed=%d skipped=0\n' "$PASS_COUNT" "$FAIL_COUNT"
        printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
        if [[ $status -eq 0 ]]; then
            printf 'RESULT: PASS\n'
        else
            printf 'RESULT: FAIL\n'
        fi
    fi
    exec 1>&3 2>&4
    cat "$VERIFY_LOG"
    exit "$status"
}
trap cleanup EXIT
trap 'stop_on_signal 129' HUP
trap 'stop_on_signal 130' INT
trap 'stop_on_signal 143' TERM

run_step() {
    local name="$1"
    local seconds="$2"
    shift 2
    printf '\n[verify] === %s ===\n' "$name"
    python3 "$WORK_ROOT/scripts/run_with_timeout.py" "$seconds" -- "$@" &
    STEP_PID=$!
    if wait "$STEP_PID"; then
        STEP_PID=""
        PASS_COUNT=$((PASS_COUNT + 1))
        log "PASS: $name"
    else
        STEP_PID=""
        FAIL_COUNT=$((FAIL_COUNT + 1))
        log "FAIL: $name"
    fi
    return 0
}

[[ -f "$STATE_FILE" ]] || preflight_die "먼저 ./prepare.sh를 실행하십시오."
marker_error="$(python3 - "$STATE_FILE" <<'PY'
import json
import sys
try:
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    print(exc)
    raise SystemExit(1)
required = {
    "guide_id", "head_commit", "source_fingerprint", "index_fingerprint",
    "python_version", "git_version", "make_version", "compiler_version",
    "rsync_version",
}
missing = sorted(key for key in required if not isinstance(payload.get(key), str) or not payload[key])
if payload.get("schema_version") != 1 or payload.get("c11_posix_threads") is not True or payload.get("asan_ubsan") is not True or missing:
    print("schema 또는 필수 field가 올바르지 않음: " + ", ".join(missing))
    raise SystemExit(1)
PY
)" || preflight_die "prepare marker가 손상되었습니다: $marker_error"

read_state() {
    python3 - "$STATE_FILE" "$1" <<'PY'
import json
import sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
value = payload.get(sys.argv[2])
if not isinstance(value, (str, int, bool)):
    raise SystemExit(1)
print(value)
PY
}

[[ "$(read_state guide_id)" == "$GUIDE_ID" ]] || preflight_die "prepare marker의 guide ID가 다릅니다."
[[ "$(read_state head_commit)" == "$(git -C "$ROOT" rev-parse HEAD)" ]] \
    || preflight_die "HEAD가 prepare 이후 바뀌었습니다. prepare를 다시 실행하십시오."
current_source="$(python3 "$ROOT/scripts/tree-fingerprint.py" "$ROOT")"
[[ "$current_source" == "$(read_state source_fingerprint)" ]] \
    || preflight_die "source가 prepare 이후 바뀌었습니다. prepare를 다시 실행하십시오."
index_path="$(git -C "$ROOT" rev-parse --git-path index)"
[[ "$index_path" == /* ]] || index_path="$ROOT/$index_path"
current_index="$(python3 - "$index_path" <<'PY'
import hashlib
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
)"
[[ "$current_index" == "$(read_state index_fingerprint)" ]] \
    || preflight_die "Git index가 prepare 이후 바뀌었습니다."
[[ "$(read_state python_version)" == "$(python3 -c 'import platform; print(platform.python_version())')" ]] \
    || preflight_die "Python 버전이 prepare 이후 바뀌었습니다."
[[ "$(read_state git_version)" == "$(git --version)" ]] \
    || preflight_die "Git 버전이 prepare 이후 바뀌었습니다."
[[ "$(read_state make_version)" == "$(make --version | sed -n '1p')" ]] \
    || preflight_die "make 버전이 prepare 이후 바뀌었습니다."
[[ "$(read_state compiler_version)" == "$(cc --version 2>/dev/null | sed -n '1p')" ]] \
    || preflight_die "compiler 버전이 prepare 이후 바뀌었습니다."
[[ "$(read_state rsync_version)" == "$(rsync --version | sed -n '1p')" ]] \
    || preflight_die "rsync 버전이 prepare 이후 바뀌었습니다."

RUN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-computer-architecture-verify.XXXXXX")" \
    || preflight_die "외부 검증 디렉터리를 만들지 못했습니다."
case "$(cd "$RUN_DIR" && pwd -P)" in "$ROOT"|"$ROOT"/*) preflight_die "검증 디렉터리가 저장소 안에 있습니다." ;; esac
WORK_ROOT="$RUN_DIR/repo"
mkdir -p "$WORK_ROOT/.guide/$GUIDE_ID"
python3 "$ROOT/scripts/run_with_timeout.py" 60 -- \
    rsync -a --exclude=.git --exclude=.guide --exclude=workspace --exclude=build \
    --exclude=__pycache__ --exclude='*.py[co]' "$ROOT/" "$WORK_ROOT/" &
STEP_PID=$!
wait "$STEP_PID" || preflight_die "격리 source 복사가 실패했습니다."
STEP_PID=""
cp "$STATE_FILE" "$WORK_ROOT/.guide/$GUIDE_ID/prepared.json"
export PYTHONDONTWRITEBYTECODE=1
cd "$WORK_ROOT"

run_step "저장소 구조·문서·학습 계약" 60 python3 scripts/validate_docs.py
run_step "validator mutant suite" 120 python3 scripts/test-validator.py
run_step "prepare marker 누락·손상·stale 회귀" 180 python3 scripts/test-prepare-marker.py
run_step "VERIFY_LOG preflight regression" 60 python3 scripts/test-verify-preflight.py
run_step "workspace 경계·symlink·덮어쓰기 안전성" 120 python3 scripts/test-workspace-tools.py
run_step "owned process-group signal/timeout cleanup" 30 python3 scripts/test-runner-safety.py
run_step "셸 문법" 60 bash -c 'while IFS= read -r -d "" script; do bash -n "$script"; done < <(find . -type f -name "*.sh" -not -path "*/workspace/*" -print0)'
run_step "processor-model reference·skeleton 계약" 300 make -C exercises/processor-model check
run_step "processor-model 단계별 결함 검출" 300 python3 scripts/test-exercise-quality.py
run_step "C11 관찰 예제" 180 make examples-check
run_step "C 예제 ASan·UBSan" 180 env GUIDE_SANITIZE=1 bash scripts/check-sanitizers.sh
run_step "stage-09 vector checksum·보고서" 180 make stage-09

after_source="$(python3 "$ROOT/scripts/tree-fingerprint.py" "$ROOT")"
if [[ "$after_source" != "$current_source" ]]; then
    FAIL_COUNT=$((FAIL_COUNT + 1)); log "FAIL: verify가 원본 source tree를 변경했습니다."
fi
after_index="$(python3 - "$index_path" <<'PY'
import hashlib
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
)"
if [[ "$after_index" != "$current_index" ]]; then
    FAIL_COUNT=$((FAIL_COUNT + 1)); log "FAIL: verify가 원본 Git index를 변경했습니다."
fi
[[ $FAIL_COUNT -eq 0 ]] || exit 1
log "모든 필수 검증을 통과했습니다."
