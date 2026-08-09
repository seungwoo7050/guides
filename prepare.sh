#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 이상이 필요합니다.')
PY

BEFORE=$(python3 -B scripts/fingerprint.py "$ROOT")
MARKER="$ROOT/.guide/data-engineering/prepared.json"
mkdir -p "$(dirname "$MARKER")"
python3 - "$MARKER" "$BEFORE" <<'PY'
import json
import platform
import sys
from pathlib import Path
path = Path(sys.argv[1])
fingerprint = sys.argv[2]
path.write_text(json.dumps({
    'guide_id': 'data-engineering',
    'source_fingerprint': fingerprint,
    'python': platform.python_version(),
    'contract_version': 1,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY
AFTER=$(python3 -B scripts/fingerprint.py "$ROOT")
if [ "$BEFORE" != "$AFTER" ]; then
  echo 'prepare가 source를 변경했습니다.' >&2
  exit 1
fi
printf 'PREPARED data-engineering %s\n' "$BEFORE"
