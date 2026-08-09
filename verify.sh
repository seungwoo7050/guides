#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER="$ROOT/.guide/embedded-systems/prepared.json"
RUNNER="$ROOT/scripts/run_with_timeout.py"
TMP=
LOG=

fail() {
  echo "ERROR: $*" >&2
  test -z "$LOG" || echo "VERIFY LOG $LOG" >&2
  exit 1
}

cleanup() {
  status=$?
  trap - EXIT HUP INT TERM
  if test -n "$TMP" && test -d "$TMP" && test ! -L "$TMP"; then
    rm -rf -- "$TMP"
  fi
  test -z "$LOG" || echo "VERIFY LOG $LOG"
  exit "$status"
}
trap cleanup EXIT HUP INT TERM

command -v "$PYTHON" >/dev/null 2>&1 || fail "Python이 없습니다: $PYTHON"
test -x "$RUNNER" || fail "timeout runner가 없습니다: $RUNNER"
test -f "$MARKER" && test ! -L "$MARKER" || fail "먼저 ./prepare.sh를 실행하십시오."
"$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --check "$MARKER" || fail "prepare marker가 stale합니다."

if test -n "${VERIFY_LOG:-}"; then
  case "$VERIFY_LOG" in
    /*) ;;
    *) fail "VERIFY_LOG는 절대 경로여야 합니다." ;;
  esac
  test ! -e "$VERIFY_LOG" && test ! -L "$VERIFY_LOG" || fail "VERIFY_LOG가 이미 존재하거나 symlink입니다: $VERIFY_LOG"
  log_parent=$(dirname -- "$VERIFY_LOG")
  test -d "$log_parent" && test ! -L "$log_parent" || fail "VERIFY_LOG parent는 기존 실제 directory여야 합니다."
  log_parent=$(CDPATH= cd -- "$log_parent" && pwd -P)
  LOG="$log_parent/$(basename -- "$VERIFY_LOG")"
  case "$LOG" in
    "$ROOT"|"$ROOT"/*) fail "VERIFY_LOG는 저장소 밖에 두어야 합니다." ;;
  esac
  umask 077
  (set -C; : > "$LOG") 2>/dev/null || fail "VERIFY_LOG를 독점 생성할 수 없습니다."
else
  LOG=$(mktemp "${TMPDIR:-/tmp}/embedded-systems-verify-log.XXXXXX") || fail "검증 로그를 만들 수 없습니다."
fi
case "$(CDPATH= cd -- "$(dirname -- "$LOG")" && pwd -P)/$(basename -- "$LOG")" in
  "$ROOT"|"$ROOT"/*) fail "검증 로그는 저장소 밖에 두어야 합니다." ;;
esac

TMP=$(mktemp -d "${TMPDIR:-/tmp}/embedded-systems-verify.XXXXXX") || fail "임시 directory를 만들 수 없습니다."
"$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --print > "$TMP/source-before.json"

"$PYTHON" - "$ROOT" "$TMP/repo" <<'PY'
import shutil
import sys
from pathlib import Path
source = Path(sys.argv[1])
dest = Path(sys.argv[2])
shutil.copytree(
    source,
    dest,
    symlinks=True,
    ignore=shutil.ignore_patterns('.git', '.guide', '__pycache__', '*.pyc', '*.log', 'workspace', 'capstone-workspace', 'build'),
)
PY

run_step() {
  label=$1
  timeout=$2
  shift 2
  {
    echo "== $label =="
    "$PYTHON" "$RUNNER" --timeout "$timeout" -- "$@"
  } >>"$LOG" 2>&1 || {
    cat "$LOG" >&2
    fail "$label 실패"
  }
}

cd "$TMP/repo"
run_step "layout and links" 30 "$PYTHON" scripts/check_docs.py
run_step "Python syntax" 30 sh -c 'PYTHONPYCACHEPREFIX="$1" "$2" -m compileall -q scripts examples' _ "$TMP/pycache" "$PYTHON"
run_step "state models" 30 "$PYTHON" -m unittest discover -s examples/tests -v
run_step "validator negative tests" 30 "$PYTHON" scripts/test_verifier.py
run_step "workspace helper" 30 sh -c './scripts/new-workspace.sh exercises/03-sensor-driver-state-machine "$1" && test -f "$1/design.md"' _ "$TMP/workspace-smoke"
run_step "clean and repeat" 30 sh -c 'make clean && "$1" scripts/check_docs.py && "$1" -m unittest discover -s examples/tests -q' _ "$PYTHON"

cd "$ROOT"
"$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --print > "$TMP/source-after.json"
cmp -s "$TMP/source-before.json" "$TMP/source-after.json" || fail "verify가 원본 source 또는 Git state를 변경했습니다."
echo "VERIFY OK" >>"$LOG"
cat "$LOG"
