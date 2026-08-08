#!/usr/bin/env bash
set -Eeuo pipefail

export GIT_OPTIONAL_LOCKS=0

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="operating-systems"
MARKER="$ROOT/.guide/$GUIDE_ID/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
RUNNER="$ROOT/scripts/run_with_timeout.py"
VERIFY_LOG="${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-os-verify-$(date -u +%Y%m%dT%H%M%SZ)-$$.log}"
WORK_DIR=""
COPY_ROOT=""
SOURCE_BEFORE=""
SOURCE_AFTER=""
COPY_BEFORE=""
COPY_AFTER=""
INDEX_BEFORE=""
READ_ONLY_INDEX=""
ACTIVE_RUNNER=""
PASSED=0
FAILED=0
SKIPPED=0
FINISHED=0
SIGNAL_RECORDED=0

exec 3>&1 4>&2

preflight_output() {
  printf '[verify] ERROR: %s\n' "$1" >&2
  printf 'passed=0 failed=1 skipped=0\n' >&2
  printf 'VERIFY LOG: %s\n' "$VERIFY_LOG" >&2
  printf 'RESULT: FAIL\n' >&2
  exit 2
}

validate_log_path() {
  [[ "$VERIFY_LOG" == /* ]] || preflight_output 'VERIFY_LOG는 절대 경로여야 합니다.'
  [[ ! -L "$VERIFY_LOG" ]] || preflight_output 'VERIFY_LOG leaf symlink는 허용하지 않습니다.'
  local canonical parent
  canonical="$(python3 - "$VERIFY_LOG" <<'PY'
import os
import sys
print(os.path.realpath(sys.argv[1]))
PY
)" || preflight_output 'VERIFY_LOG 경로를 확인할 수 없습니다.'
  case "$canonical" in
    "$ROOT"|"$ROOT"/*) preflight_output 'VERIFY_LOG는 저장소 밖에 있어야 합니다.' ;;
  esac
  [[ ! -d "$canonical" ]] || preflight_output 'VERIFY_LOG leaf는 디렉터리일 수 없습니다.'
  parent="$(dirname -- "$canonical")"
  mkdir -p -- "$parent" || preflight_output '로그 디렉터리를 만들 수 없습니다.'
  VERIFY_LOG="$canonical"
  : >"$VERIFY_LOG" || preflight_output '로그 파일에 쓸 수 없습니다.'
}

validate_log_path
exec >>"$VERIFY_LOG" 2>&1

log() { printf '[verify] %s\n' "$*"; }
preflight_fail() { FAILED=$((FAILED + 1)); log "ERROR: $*"; exit 2; }

first_line() {
  python3 -c 'import sys; lines=sys.stdin.read().splitlines(); print(lines[0].strip() if lines else "")'
}

git_version() { git --version; }
make_version() { make --version 2>&1 | first_line; }
rsync_version() { rsync --version 2>&1 | first_line; }
bash_version() { bash --version 2>&1 | first_line; }
cc_version() { cc --version 2>&1 | first_line; }

marker_field() {
  python3 - "$MARKER" "$1" <<'PY'
import json
from pathlib import Path
import sys

try:
    value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))[sys.argv[2]]
except (OSError, KeyError, TypeError, ValueError) as error:
    raise SystemExit(f"marker field 오류: {error}")
if not isinstance(value, (str, int)):
    raise SystemExit("marker scalar field가 아닙니다")
print(value)
PY
}

index_fingerprint() {
  "$STATE_TOOL" index --root "$ROOT"
}

cleanup() {
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" && ! -L "$WORK_DIR" ]]; then
    rm -rf -- "$WORK_DIR"
  fi
}

stop_on_signal() {
  local signum=$1
  local code=$2
  trap '' HUP INT TERM
  if (( SIGNAL_RECORDED == 0 )); then
    SIGNAL_RECORDED=1
    FAILED=$((FAILED + 1))
    log "[FAIL] top-level signal=$signum; owned foreground process tree를 종료합니다."
  fi
  if [[ -n "$ACTIVE_RUNNER" ]]; then
    kill -"$signum" "$ACTIVE_RUNNER" 2>/dev/null || true
    wait "$ACTIVE_RUNNER" 2>/dev/null || true
    ACTIVE_RUNNER=""
  fi
  exit "$code"
}

finish() {
  local status=$?
  (( FINISHED == 0 )) || exit "$status"
  FINISHED=1
  trap - EXIT
  trap '' HUP INT TERM
  if [[ -n "$ACTIVE_RUNNER" ]]; then
    kill -TERM "$ACTIVE_RUNNER" 2>/dev/null || true
    wait "$ACTIVE_RUNNER" 2>/dev/null || true
    ACTIVE_RUNNER=""
  fi
  if [[ -n "$SOURCE_AFTER" && -x "$STATE_TOOL" ]]; then
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 || status=1
    if [[ -n "$SOURCE_BEFORE" ]] && ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      log '[FAIL] verify가 원본 source bytes·mode·directory·symlink를 변경했습니다.'
      FAILED=$((FAILED + 1))
      status=1
    fi
  fi
  if [[ -n "$INDEX_BEFORE" && -x "$STATE_TOOL" ]]; then
    if [[ "$INDEX_BEFORE" != "$(index_fingerprint)" ]]; then
      log '[FAIL] verify가 raw Git index를 변경했습니다.'
      FAILED=$((FAILED + 1))
      status=1
    fi
  fi
  cleanup
  if (( status != 0 || FAILED != 0 || SKIPPED != 0 )); then
    (( FAILED == 0 )) && FAILED=1
    (( status == 0 )) && status=1
    printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
    printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
    printf 'RESULT: FAIL\n'
    cat -- "$VERIFY_LOG" >&3 || true
    exit "$status"
  fi
  printf 'passed=%d failed=0 skipped=0\n' "$PASSED"
  printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
  printf 'RESULT: PASS\n'
  cat -- "$VERIFY_LOG" >&3 || true
}

run_owned() {
  local timeout=$1
  shift
  "$RUNNER" --timeout "$timeout" -- "$@" &
  ACTIVE_RUNNER=$!
  local status=0
  if wait "$ACTIVE_RUNNER"; then
    status=0
  else
    status=$?
  fi
  ACTIVE_RUNNER=""
  return "$status"
}

run_required() {
  local label=$1
  local timeout=$2
  shift 2
  if ! run_owned "$timeout" "$@"; then
    preflight_fail "$label 실패"
  fi
}

run_step() {
  local label=$1
  local timeout=$2
  shift 2
  printf '\n[verify] === %s ===\n' "$label"
  if run_owned "$timeout" "$@"; then
    PASSED=$((PASSED + 1))
    log "[PASS] $label"
  else
    local status=$?
    FAILED=$((FAILED + 1))
    log "[FAIL] $label (exit=$status)"
  fi
}

main() {
  trap finish EXIT
  trap 'stop_on_signal 1 129' HUP
  trap 'stop_on_signal 2 130' INT
  trap 'stop_on_signal 15 143' TERM
  [[ $# -eq 0 ]] || preflight_fail '사용법: ./verify.sh'
  for command_name in git python3 rsync bash sh cmp cp mktemp make cc; do
    command -v "$command_name" >/dev/null 2>&1 || preflight_fail "필수 명령이 없습니다: $command_name"
  done
  [[ -x "$STATE_TOOL" ]] || preflight_fail 'repository state 도구가 없습니다.'
  [[ -x "$RUNNER" ]] || preflight_fail 'timeout/process-tree runner가 없습니다.'
  INDEX_BEFORE="$(index_fingerprint)" || preflight_fail 'raw Git index를 읽을 수 없습니다.'
  [[ ! -L "$ROOT/.guide" && ! -L "$ROOT/.guide/$GUIDE_ID" && ! -L "$MARKER" ]] \
    || preflight_fail '.guide marker 경로에 symbolic link를 사용할 수 없습니다.'
  [[ -f "$MARKER" ]] || preflight_fail '먼저 ./prepare.sh를 실행하십시오.'
  [[ "$(marker_field guide_id)" == "$GUIDE_ID" ]] || preflight_fail '다른 가이드의 prepare marker입니다.'
  [[ "$(marker_field schema_version)" == 1 ]] || preflight_fail '지원하지 않는 marker schema입니다.'
  [[ "$(marker_field head_commit)" == "$(git -C "$ROOT" rev-parse HEAD)" ]] || preflight_fail 'HEAD가 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field source_fingerprint)" == "$("$STATE_TOOL" fingerprint --root "$ROOT")" ]] \
    || preflight_fail 'source가 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field index_fingerprint)" == "$INDEX_BEFORE" ]] || preflight_fail 'Git index가 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field python_version)" == "$(python3 -c 'import platform; print(platform.python_version())')" ]] \
    || preflight_fail 'Python version이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field git_version)" == "$(git_version)" ]] || preflight_fail 'Git version이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field make_version)" == "$(make_version)" ]] || preflight_fail 'make version이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field rsync_version)" == "$(rsync_version)" ]] || preflight_fail 'rsync version이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field bash_version)" == "$(bash_version)" ]] || preflight_fail 'Bash version이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field cc_path)" == "$(command -v cc)" ]] || preflight_fail 'C compiler 경로가 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field cc_version)" == "$(cc_version)" ]] || preflight_fail 'C compiler version이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field platform_system)" == "$(python3 -c 'import platform; print(platform.system())')" ]] \
    || preflight_fail '운영체제 platform이 prepare 이후 바뀌었습니다.'
  python3 - <<'PY' || preflight_fail 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

  WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-os-verify.XXXXXX")"
  COPY_ROOT="$WORK_DIR/repository"
  SOURCE_BEFORE="$WORK_DIR/source-before.json"
  SOURCE_AFTER="$WORK_DIR/source-after.json"
  COPY_BEFORE="$WORK_DIR/copy-before.json"
  COPY_AFTER="$WORK_DIR/copy-after.json"
  READ_ONLY_INDEX="$WORK_DIR/read-only.index"
  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  mkdir -p -- "$COPY_ROOT"
  run_required '격리 source 복사' 30 rsync -a --exclude=.git --exclude=.guide --exclude=build \
    --exclude=build-sanitize --exclude=workspace --exclude=__pycache__ --exclude='*.pyc' "$ROOT/" "$COPY_ROOT/"
  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_BEFORE"

  cp -- "$("$STATE_TOOL" index-path --root "$ROOT")" "$READ_ONLY_INDEX"
  GIT_INDEX_FILE="$READ_ONLY_INDEX" git -C "$ROOT" diff --check
  GIT_INDEX_FILE="$READ_ONLY_INDEX" git -C "$ROOT" diff --cached --check
  PASSED=$((PASSED + 1))
  log '[PASS] working/staged diff hygiene, optional-lock raw index와 prepare fingerprint'

  cd -- "$COPY_ROOT"
  if [[ -n "${GUIDE_VERIFY_SIGNAL_PROBE:-}" ]]; then
    [[ "$GUIDE_VERIFY_SIGNAL_PROBE" == /* ]] || preflight_fail 'signal probe 경로는 절대 경로여야 합니다.'
    run_step 'top-level signal cleanup probe' 300 python3 scripts/test-checker.py \
      --signal-probe "$GUIDE_VERIFY_SIGNAL_PROBE" "$WORK_DIR/signal-owned.residual"
    preflight_fail 'signal probe가 중단되지 않고 끝났습니다.'
  fi

  run_step '정확한 저장소 구조·문서·학습 계약' 30 python3 scripts/validate.py
  run_step 'validator pedagogy/layout mutant suite' 60 python3 scripts/test-validator.py
  run_step 'directory/index/clean 공통 안전성' 60 python3 scripts/test-common-safety.py
  run_step 'VERIFY_LOG 모든 preflight 안전성' 30 python3 scripts/test-verify-preflight.py
  run_step 'workspace traversal/alias/exclusive-race 안전성' 30 python3 scripts/test-workspace-tools.py
  run_step 'shell syntax' 30 bash -c '
    set -e
    while IFS= read -r script; do
      case "$(head -n 1 "$script")" in
        *bash*) bash -n "$script" ;;
        *) sh -n "$script" ;;
      esac
    done < <(find prepare.sh verify.sh scripts exercises -type f -name "*.sh" | sort)
  '
  run_step 'Python syntax' 30 bash -c '
    set -e
    cache=$1
    while IFS= read -r source; do
      PYTHONPYCACHEPREFIX="$cache" python3 -m py_compile "$source"
    done < <(find scripts exercises -type f -name "*.py" | sort)
  ' _ "$WORK_DIR/python-cache"
  run_step 'C11 observable examples' 90 make -C examples verify
  run_step 'C address/undefined sanitizers' 120 make -C examples sanitizer-check
  run_step '8 checkpoints/skeleton/failure/CLI/timeout/signal' 120 make -C exercises/kernel-model verify
  run_step 'top-level verify signal/process-tree cleanup' 90 python3 scripts/test-verify-signal.py

  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_AFTER"
  if cmp -s "$COPY_BEFORE" "$COPY_AFTER"; then
    PASSED=$((PASSED + 1))
    log '[PASS] isolated source bytes/directory mode/symlink stability'
  else
    FAILED=$((FAILED + 1))
    log '[FAIL] isolated 검사가 source input을 변경했습니다.'
  fi
}

main "$@"
