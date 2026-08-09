#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10 이상이 필요합니다.')
print('Python', '.'.join(map(str, sys.version_info[:3])))
PY

python3 scripts/verify_repository.py --quick

python3 - <<'PY'
from __future__ import annotations

import json
import platform
from pathlib import Path
import sys

sys.path.insert(0, str(Path('scripts').resolve()))
from source_fingerprint import fingerprint

value, count = fingerprint(Path.cwd())
marker = Path('.guide/platform-engineering/prepared.json')
marker.parent.mkdir(parents=True, exist_ok=True)
marker.write_text(json.dumps({
    'guide': 'platform-engineering',
    'python': platform.python_version(),
    'sourceSha256': value,
    'sourceFiles': count,
    'preparation': 'source fingerprint only; no system packages or platform tools installed'
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('PREPARED', marker)
print('SOURCE SHA256', value)
PY
