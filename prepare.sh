#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"

PYTHON=${PYTHON:-python3}
STATE_ROOT="$ROOT/.guide"
STATE_DIR="$STATE_ROOT/embedded-systems"
MARKER="$STATE_DIR/prepared.json"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

for command_name in "$PYTHON" git make sh; do
  command -v "$command_name" >/dev/null 2>&1 || fail "필수 명령이 없습니다: $command_name"
done

"$PYTHON" - <<'PY' || fail "Python 3.10 이상이 필요합니다."
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY

test ! -L "$STATE_ROOT" || fail ".guide symlink는 허용하지 않습니다."
test ! -L "$STATE_DIR" || fail ".guide/embedded-systems symlink는 허용하지 않습니다."
umask 077
mkdir -p "$STATE_DIR/pycache"

sh -n prepare.sh verify.sh scripts/new-workspace.sh
PYTHONPYCACHEPREFIX="$STATE_DIR/pycache" "$PYTHON" -m py_compile \
  scripts/source_fingerprint.py \
  scripts/check_docs.py \
  scripts/test_verifier.py \
  scripts/run_with_timeout.py \
  examples/interrupt-event-model/model.py \
  examples/update-state-model/model.py \
  examples/tests/test_models.py

"$PYTHON" scripts/check_docs.py
"$PYTHON" scripts/source_fingerprint.py --root "$ROOT" --write "$MARKER"
echo "PREPARE OK"
