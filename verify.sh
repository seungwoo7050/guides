#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER="$ROOT/.guide/embedded-systems/prepared.json"
TMP=
LOG=

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

remove_temp() {
  if test -n "$TMP" && test -d "$TMP" && test ! -L "$TMP"; then
    rm -rf -- "$TMP"
  fi
}

on_exit() {
  status=$1
  trap - EXIT HUP INT TERM
  remove_temp
  test -z "$LOG" || echo "VERIFY LOG $LOG"
  exit "$status"
}

on_signal() {
  code=$1
  trap - EXIT HUP INT TERM
  remove_temp
  test -z "$LOG" || echo "VERIFY LOG $LOG"
  exit "$code"
}

trap 'on_exit $?' EXIT
trap 'on_signal 129' HUP
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

command -v "$PYTHON" >/dev/null 2>&1 || fail "Python이 없습니다: $PYTHON"
test -f "$MARKER" && test ! -L "$MARKER" || fail "먼저 ./prepare.sh를 실행하십시오."
"$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --check "$MARKER" || fail "prepare marker가 stale합니다."

if test -n "${VERIFY_LOG:-}"; then
  LOG=$(
    "$PYTHON" - "$ROOT" "$VERIFY_LOG" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
raw = sys.argv[2]
if "\n" in raw or "\r" in raw:
    raise SystemExit("ERROR: VERIFY_LOG path contains a newline")
candidate = Path(raw)
if not candidate.is_absolute():
    raise SystemExit("ERROR: VERIFY_LOG는 절대 경로여야 합니다.")
lexical = Path(os.path.abspath(candidate))
if os.path.lexists(lexical):
    raise SystemExit(f"ERROR: VERIFY_LOG가 이미 존재하거나 symlink입니다: {lexical}")
parent = lexical.parent
try:
    resolved_parent = parent.resolve(strict=True)
except OSError as error:
    raise SystemExit(f"ERROR: VERIFY_LOG parent는 기존 실제 directory여야 합니다: {error}")
if parent != resolved_parent or parent.is_symlink():
    raise SystemExit("ERROR: VERIFY_LOG parent는 symlink 경로를 포함할 수 없습니다.")
if not parent.is_dir():
    raise SystemExit("ERROR: VERIFY_LOG parent는 directory여야 합니다.")
try:
    lexical.relative_to(root)
except ValueError:
    pass
else:
    raise SystemExit("ERROR: VERIFY_LOG는 저장소 밖에 두어야 합니다.")
print(lexical)
PY
  ) || exit $?
  umask 077
  (set -C; : > "$LOG") 2>/dev/null || fail "VERIFY_LOG를 독점 생성할 수 없습니다."
  test -f "$LOG" && test ! -L "$LOG" || fail "VERIFY_LOG regular file 생성에 실패했습니다."
else
  LOG=$(mktemp "${TMPDIR:-/tmp}/embedded-systems-verify-log.XXXXXX") || fail "검증 로그를 만들 수 없습니다."
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/embedded-systems-verify.XXXXXX") || fail "임시 directory를 만들 수 없습니다."
"$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --print > "$TMP/original-before.json"

assert_original_unchanged() {
  "$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --print > "$TMP/original-after.json"
  cmp -s "$TMP/original-before.json" "$TMP/original-after.json" || fail "verify가 원본 source, Git HEAD 또는 raw index를 변경했습니다."
}

# Internal probes are used only by scripts/test_verify_safety.py.  They exercise
# log ownership and signal cleanup without recursively running the full suite.
case "${VERIFY_SAFETY_PROBE:-}" in
  success)
    echo "VERIFY PROBE OK $TMP"
    echo "VERIFY PROBE OK" >> "$LOG"
    assert_original_unchanged
    exit 0
    ;;
  wait)
    echo "VERIFY PROBE READY $TMP"
    echo "VERIFY PROBE WAIT" >> "$LOG"
    while :; do sleep 1; done
    ;;
  "") ;;
  *) fail "unknown VERIFY_SAFETY_PROBE" ;;
esac

"$PYTHON" - "$ROOT" "$TMP/repo" <<'PY'
import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
shutil.copytree(
    source,
    destination,
    symlinks=True,
    ignore=shutil.ignore_patterns(
        ".git", ".guide", "__pycache__", "*.pyc", "*.log",
        "workspace", "capstone-workspace", "build",
    ),
)
PY

RUNNER="$TMP/repo/scripts/run_with_timeout.py"
test -x "$RUNNER" || fail "timeout runner가 없거나 실행 불가능합니다: $RUNNER"

run_step() {
  label=$1
  timeout=$2
  shift 2
  {
    echo "== $label =="
    "$PYTHON" "$RUNNER" --timeout "$timeout" -- "$@"
  } >> "$LOG" 2>&1 || {
    cat "$LOG" >&2
    fail "$label 실패"
  }
}

cd "$TMP/repo"
export PYTHONDONTWRITEBYTECODE=1
run_step "shell syntax" 30 sh -n prepare.sh verify.sh scripts/new-workspace.sh
run_step "layout and local links" 30 "$PYTHON" scripts/check_docs.py
run_step "Python syntax" 60 sh -c 'PYTHONPYCACHEPREFIX="$1" "$2" -m compileall -q scripts examples exercises capstone' _ "$TMP/pycache" "$PYTHON"
run_step "state models" 45 "$PYTHON" -m unittest discover -s examples/tests -v
run_step "exercise public contracts" 120 "$PYTHON" scripts/check_learning_contracts.py --scope exercises
run_step "capstone public contract" 90 "$PYTHON" scripts/check_learning_contracts.py --scope capstone
run_step "validator negative tests" 60 "$PYTHON" scripts/test_verifier.py
run_step "workspace safety tests" 60 "$PYTHON" scripts/test_workspace_tools.py
run_step "verifier safety tests" 90 "$PYTHON" scripts/test_verify_safety.py
run_step "clean and repeat" 60 sh -c 'make clean && "$1" scripts/check_docs.py && "$1" -m unittest discover -s examples/tests -q' _ "$PYTHON"

cd "$ROOT"
assert_original_unchanged
echo "VERIFY OK" >> "$LOG"
cat "$LOG"
