#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

PYTHON=${PYTHON:-python3}

command -v "$PYTHON" >/dev/null 2>&1 || {
  echo "ERROR: Python 3.10 이상이 필요합니다." >&2
  exit 1
}
command -v make >/dev/null 2>&1 || {
  echo "ERROR: make가 필요합니다." >&2
  exit 1
}

"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(f"ERROR: Python 3.10 이상이 필요합니다: {sys.version.split()[0]}")
print(f"PYTHON OK {sys.version.split()[0]}")
PY

make clean >/dev/null
"$PYTHON" -m py_compile \
  scripts/source_fingerprint.py \
  scripts/check_docs.py \
  scripts/test_verifier.py \
  examples/interrupt-event-model/model.py \
  examples/update-state-model/model.py \
  examples/tests/test_models.py
make clean >/dev/null

"$PYTHON" scripts/source_fingerprint.py \
  --root "$ROOT" \
  --write .guide/embedded-systems/prepared.json
