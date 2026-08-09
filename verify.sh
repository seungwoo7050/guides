#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

MARKER=.guide/agentic-systems/prepared.json
if [ ! -f "$MARKER" ]; then
  echo '먼저 ./prepare.sh를 실행하십시오.' >&2
  exit 1
fi

python3 scripts/check_docs.py

set -- $(python3 scripts/source_fingerprint.py)
CURRENT=$1
COUNT=$2
EXPECTED=$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path('.guide/agentic-systems/prepared.json').read_text(encoding='utf-8'))['source_sha256'])
PY
)

if [ "$CURRENT" != "$EXPECTED" ]; then
  echo 'prepare 이후 source가 변경되었습니다. ./prepare.sh를 다시 실행하십시오.' >&2
  echo "expected=$EXPECTED" >&2
  echo "current=$CURRENT" >&2
  exit 1
fi

printf 'VERIFY OK source_files=%s sha256=%s\n' "$COUNT" "$CURRENT"
