#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER=.guide/embedded-systems/prepared.json

"$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --check "$MARKER"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/embedded-systems-verify.XXXXXX")
DEFAULT_LOG=$(mktemp "${TMPDIR:-/tmp}/embedded-systems-verify.XXXXXX.log")
LOG=${VERIFY_LOG:-$DEFAULT_LOG}

case "$LOG" in
  /*) ;;
  *)
    echo "ERROR: VERIFY_LOG는 저장소 밖 절대 경로여야 합니다." >&2
    rm -rf "$TMP"
    exit 1
    ;;
esac
case "$LOG" in
  "$ROOT"|"$ROOT"/*)
    echo "ERROR: VERIFY_LOG는 저장소 밖에 두어야 합니다." >&2
    rm -rf "$TMP"
    exit 1
    ;;
esac
if [ -L "$LOG" ]; then
  echo "ERROR: symlink log path를 거부합니다: $LOG" >&2
  rm -rf "$TMP"
  exit 1
fi

cleanup() {
  status=$?
  rm -rf "$TMP"
  echo "VERIFY LOG $LOG"
  exit "$status"
}
trap cleanup EXIT HUP INT TERM

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
    ignore=shutil.ignore_patterns('.git', '.guide', '__pycache__', '*.pyc', '*.log', 'workspace', 'build'),
)
PY

(
  set -eu
  cd "$TMP/repo"
  echo "== layout and links =="
  "$PYTHON" scripts/check_docs.py
  echo "== Python syntax =="
  "$PYTHON" -m compileall -q scripts examples
  echo "PYTHON COMPILE OK"
  echo "== state models =="
  "$PYTHON" -m unittest discover -s examples/tests -v
  echo "== validator negative tests =="
  "$PYTHON" scripts/test_verifier.py
  echo "== workspace helper =="
  ./scripts/new-workspace.sh exercises/03-sensor-driver-state-machine "$TMP/workspace-smoke"
  test -f "$TMP/workspace-smoke/design.md"
  echo "WORKSPACE OK"
  echo "== clean and repeat =="
  make clean
  "$PYTHON" scripts/check_docs.py
  "$PYTHON" -m unittest discover -s examples/tests -q
  echo "VERIFY OK"
) >"$LOG" 2>&1 || {
  cat "$LOG" >&2
  exit 1
}

cat "$LOG"
