#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MARKER="$ROOT/.guide/language-implementation/prepared.json"

if [ ! -f "$MARKER" ]; then
  echo "먼저 ./prepare.sh를 실행하십시오." >&2
  exit 1
fi

EXPECTED=$(python3 - "$MARKER" <<'PY2'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["source_sha256"])
PY2
)
ACTUAL=$(cd "$ROOT" && python3 scripts/source_fingerprint.py)
if [ "$EXPECTED" != "$ACTUAL" ]; then
  echo "prepare 이후 source가 변경되었습니다." >&2
  echo "expected=$EXPECTED" >&2
  echo "actual=$ACTUAL" >&2
  exit 1
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/guide-language-implementation.XXXXXX")
LOG=$(mktemp "${TMPDIR:-/tmp}/guide-language-implementation.XXXXXX.log")
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT HUP INT TERM

mkdir -p "$TMP/repo"
(
  cd "$ROOT"
  tar -cf - \
    --exclude='./.git' \
    --exclude='./.guide' \
    --exclude='./.workspaces' \
    --exclude='*/__pycache__' \
    .
) | (cd "$TMP/repo" && tar -xf -)

set +e
(
  set -eu
  cd "$TMP/repo"
  python3 scripts/check_structure.py
  python3 scripts/check_links.py
  python3 scripts/check_docs.py
  python3 scripts/check_capstone_spec.py
  python3 scripts/run_examples.py
  python3 scripts/source_fingerprint.py --json
) >"$LOG" 2>&1
STATUS=$?
set -e
cat "$LOG"
if [ "$STATUS" -ne 0 ]; then
  echo "VERIFY FAILED log=$LOG" >&2
  exit "$STATUS"
fi

AFTER=$(cd "$ROOT" && python3 scripts/source_fingerprint.py)
if [ "$EXPECTED" != "$AFTER" ]; then
  echo "검증 중 원본 source가 변경되었습니다." >&2
  echo "expected=$EXPECTED" >&2
  echo "after=$AFTER" >&2
  exit 1
fi

printf 'VERIFY OK\n'
printf 'LOG %s\n' "$LOG"
