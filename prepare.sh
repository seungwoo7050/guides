#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 - <<'PY'
from __future__ import annotations
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10 이상이 필요합니다.')

sys.path.insert(0, str(root / 'scripts'))
from source_fingerprint import fingerprint


def command_version(name: str, args: list[str]) -> dict[str, object]:
    path = shutil.which(name)
    if path is None:
        return {'available': False}
    try:
        result = subprocess.run([path, *args], text=True, capture_output=True, timeout=5, check=False)
        line = (result.stdout or result.stderr).strip().splitlines()
        return {'available': result.returncode == 0, 'path': path, 'version': line[0] if line else None}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'available': False, 'path': path, 'error': str(exc)}


def pkg_config_version(package: str) -> dict[str, object]:
    path = shutil.which('pkg-config')
    if path is None:
        return {'available': False}
    result = subprocess.run([path, '--modversion', package], text=True, capture_output=True, timeout=5, check=False)
    return {
        'available': result.returncode == 0,
        'version': result.stdout.strip() if result.returncode == 0 else None,
        'diagnostic': result.stderr.strip() or None,
    }

sha, count = fingerprint(root)
payload = {
    'guide': 'computer-graphics',
    'prepared_schema_version': 1,
    'python': platform.python_version(),
    'platform': platform.platform(),
    'source_sha256': sha,
    'source_file_count': count,
    'required': {'python': {'available': True, 'version': platform.python_version()}},
    'optional': {
        'cxx': command_version('c++', ['--version']),
        'cmake': command_version('cmake', ['--version']),
        'sdl3_pkg_config': pkg_config_version('sdl3'),
        'renderdoccmd': command_version('renderdoccmd', ['--version']),
    },
}
marker = root / '.guide/computer-graphics/prepared.json'
marker.parent.mkdir(parents=True, exist_ok=True)
marker.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(f'PREPARED {marker.relative_to(root)}')
print(f'SOURCE_SHA256 {sha}')
for name, value in payload['optional'].items():
    status = 'FOUND' if value.get('available') else 'SKIP'
    version = value.get('version') or ''
    print(f'{status} optional {name} {version}'.rstrip())
PY
