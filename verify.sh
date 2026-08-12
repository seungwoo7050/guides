#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_OPTIONAL_LOCKS=0

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="algorithms"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
VERIFY_LOG="${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-algorithms-verify-$(date -u +%Y%m%dT%H%M%SZ)-$$.log}"
WORK_DIR=""
COPY_ROOT=""
SOURCE_BEFORE=""
SOURCE_AFTER=""
COPY_BEFORE=""
COPY_AFTER=""
INDEX_BEFORE=""
INDEX_AFTER=""
PASSED=0
FAILED=0
SKIPPED=0
FINISHED=0
STEP_PID=""

preflight_output() {
  printf '[verify] ERROR: %s\n' "$1" >&2
  printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" 1 "$SKIPPED" >&2
  printf 'VERIFY LOG: %s\n' "$VERIFY_LOG" >&2
  printf 'RESULT: FAIL\n' >&2
  exit 2
}

validate_log_path() {
  [[ "$VERIFY_LOG" == /* ]] || preflight_output 'VERIFY_LOG는 절대 경로여야 합니다.'
  [[ ! -L "$VERIFY_LOG" ]] || preflight_output 'VERIFY_LOG symlink는 허용하지 않습니다.'
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
  parent="$(dirname -- "$canonical")"
  mkdir -p -- "$parent" || preflight_output '로그 디렉터리를 만들 수 없습니다.'
  VERIFY_LOG="$canonical"
  : >"$VERIFY_LOG" || preflight_output '로그 파일에 쓸 수 없습니다.'
}

validate_log_path
exec 3>&1 4>&2
exec >>"$VERIFY_LOG" 2>&1

log() { printf '[verify] %s\n' "$*"; }
preflight_fail() { FAILED=$((FAILED + 1)); log "ERROR: $*"; exit 2; }

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
  local index_path
  index_path="$(git_index_path)"
  python3 - "$index_path" <<'PY'
import hashlib
from pathlib import Path
import sys
path = Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
}

git_index_path() {
  local index_path
  index_path="$(git -C "$ROOT" rev-parse --git-path index)"
  [[ "$index_path" == /* ]] || index_path="$ROOT/$index_path"
  printf '%s\n' "$index_path"
}

cleanup() {
  [[ -z "$WORK_DIR" || ! -d "$WORK_DIR" ]] || rm -rf -- "$WORK_DIR"
}

stop_on_signal() {
  local code=$1
  trap - HUP INT TERM
  if [[ -n "$STEP_PID" ]]; then
    kill -TERM "$STEP_PID" >/dev/null 2>&1 || true
    wait "$STEP_PID" >/dev/null 2>&1 || true
    STEP_PID=""
  fi
  exit "$code"
}

finish() {
  local status=$?
  (( FINISHED == 0 )) || exit "$status"
  FINISHED=1
  trap - EXIT HUP INT TERM
  if [[ -n "$SOURCE_AFTER" && -x "$STATE_TOOL" ]]; then
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 || status=1
    if [[ -n "$SOURCE_BEFORE" ]] && ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      log '[FAIL] verify가 원본 source를 변경했습니다.'
      FAILED=$((FAILED + 1))
      status=1
    fi
  fi
  if [[ -n "$INDEX_BEFORE" ]]; then
    INDEX_AFTER="$(index_fingerprint)" || status=1
    if [[ "$INDEX_BEFORE" != "$INDEX_AFTER" ]]; then
      log '[FAIL] verify가 원본 Git index를 변경했습니다.'
      FAILED=$((FAILED + 1))
      status=1
    fi
  fi
  cleanup
  if (( status != 0 || FAILED != 0 || SKIPPED != 0 )); then
    (( status == 0 )) && status=1
    printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
    printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
    printf 'RESULT: FAIL\n'
    cat -- "$VERIFY_LOG" >&3 || true
    exit "$status"
  fi
  printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
  printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
  printf 'RESULT: PASS\n'
  cat -- "$VERIFY_LOG" >&3 || true
}

run_step() {
  local label=$1
  local seconds=$2
  shift 2
  printf '\n[verify] === %s ===\n' "$label"
  python3 "$COPY_ROOT/scripts/run_with_timeout.py" "$seconds" -- "$@" &
  STEP_PID=$!
  if wait "$STEP_PID"; then
    STEP_PID=""
    PASSED=$((PASSED + 1))
    log "[PASS] $label"
  else
    STEP_PID=""
    FAILED=$((FAILED + 1))
    log "[FAIL] $label"
  fi
}

check_shell_syntax() {
  while IFS= read -r script; do
    case "$(head -n 1 "$script")" in
      *bash*) bash -n "$script" ;;
      *) sh -n "$script" ;;
    esac
  done < <(find prepare.sh verify.sh scripts exercises -type f -name '*.sh' | sort)
}

check_python_syntax() {
  while IFS= read -r source; do
    PYTHONPYCACHEPREFIX="$WORK_DIR/python-cache" python3 -m py_compile "$source"
  done < <(find scripts exercises -type f -name '*.py' | sort)
}

main() {
  [[ $# -eq 0 ]] || preflight_fail '사용법: ./verify.sh'
  trap finish EXIT
  trap 'stop_on_signal 129' HUP
  trap 'stop_on_signal 130' INT
  trap 'stop_on_signal 143' TERM
  for command_name in git python3 make rsync bash sh cmp cp mktemp sed; do
    command -v "$command_name" >/dev/null 2>&1 || preflight_fail "필수 명령이 없습니다: $command_name"
  done
  [[ -x "$STATE_TOOL" ]] || preflight_fail 'repository state 도구가 없습니다.'
  [[ -f "$MARKER" ]] || preflight_fail '먼저 ./prepare.sh를 실행하십시오.'
  [[ "$(marker_field guide_id)" == "$GUIDE_ID" ]] || preflight_fail '다른 가이드의 prepare marker입니다.'
  [[ "$(marker_field schema_version)" == 1 ]] || preflight_fail '지원하지 않는 marker schema입니다.'
  [[ "$(marker_field head_commit)" == "$(git -C "$ROOT" rev-parse HEAD)" ]] || preflight_fail 'HEAD가 prepare 이후 바뀌었습니다.'
  local source_fingerprint
  source_fingerprint="$("$STATE_TOOL" fingerprint --root "$ROOT")"
  [[ "$(marker_field source_fingerprint)" == "$source_fingerprint" ]] || preflight_fail 'source가 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field index_fingerprint)" == "$(index_fingerprint)" ]] || preflight_fail 'Git index가 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field git_version)" == "$(git --version)" ]] || preflight_fail 'Git 버전이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field make_version)" == "$(make --version | sed -n '1p')" ]] || preflight_fail 'make 버전이 prepare 이후 바뀌었습니다.'
  [[ "$(marker_field rsync_version)" == "$(rsync --version | sed -n '1p')" ]] || preflight_fail 'rsync 버전이 prepare 이후 바뀌었습니다.'
  python3 - <<'PY' || preflight_fail 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

  WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-algorithms-verify.XXXXXX")"
  COPY_ROOT="$WORK_DIR/repository"
  SOURCE_BEFORE="$WORK_DIR/source-before.json"
  SOURCE_AFTER="$WORK_DIR/source-after.json"
  COPY_BEFORE="$WORK_DIR/copy-before.json"
  COPY_AFTER="$WORK_DIR/copy-after.json"
  INDEX_BEFORE="$(index_fingerprint)"
  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  mkdir -p -- "$COPY_ROOT"
  python3 "$ROOT/scripts/run_with_timeout.py" 60 -- \
    rsync -a --exclude='/.git' --exclude='/.guide/' \
      --exclude='/exercises/07-verified-algorithms-capstone/workspace/' \
      --exclude='__pycache__/' --exclude='*.py[co]' "$ROOT/" "$COPY_ROOT/" &
  STEP_PID=$!
  wait "$STEP_PID" || preflight_fail '격리 source 복사가 실패했습니다.'
  STEP_PID=""
  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_BEFORE"

  local shadow_index
  shadow_index="$WORK_DIR/index-shadow"
  cp -p -- "$(git_index_path)" "$shadow_index"
  GIT_INDEX_FILE="$shadow_index" git -C "$ROOT" diff --check
  GIT_INDEX_FILE="$shadow_index" git -C "$ROOT" diff --cached --check
  PASSED=$((PASSED + 1))
  log '[PASS] working/staged diff hygiene와 prepare fingerprint'

  cd -- "$COPY_ROOT"
  run_step '정확한 저장소 구조·문서·학습 계약' 60 python3 scripts/validate.py
  run_step 'validator mutant suite' 120 python3 scripts/test-validator.py
  run_step 'prepare marker missing/corrupt/source/tool stale' 180 python3 scripts/test-prepare-marker.py
  run_step 'VERIFY_LOG 상대·저장소·symlink 안전성' 60 python3 scripts/test-verify-preflight.py
  run_step 'workspace path/symlink/no-overwrite safety' 120 python3 scripts/test-workspace-tools.py
  run_step 'owned process-group signal/timeout cleanup' 30 python3 scripts/test-runner-safety.py
  run_step 'shell syntax' 60 bash -c 'while IFS= read -r script; do case "$(head -n 1 "$script")" in *bash*) bash -n "$script" ;; *) sh -n "$script" ;; esac; done < <(find prepare.sh verify.sh scripts exercises -type f -name "*.sh" | sort)'
  run_step 'Python syntax' 60 bash -c 'while IFS= read -r source; do PYTHONPYCACHEPREFIX="$1/python-cache" python3 -m py_compile "$source"; done < <(find scripts exercises -type f -name "*.py" | sort)' _ "$WORK_DIR"
  run_step 'reference/skeleton/broken/timeout contracts' 300 python3 scripts/test-checker.py

  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_AFTER"
  if cmp -s "$COPY_BEFORE" "$COPY_AFTER"; then
    PASSED=$((PASSED + 1))
    log '[PASS] isolated source stability'
  else
    FAILED=$((FAILED + 1))
    log '[FAIL] isolated 검사가 source input을 변경했습니다.'
  fi
}

main "$@"
