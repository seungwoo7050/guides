#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_OPTIONAL_LOCKS=0

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="computer-graphics"
STATE_ROOT="$ROOT/.guide"
STATE_DIR="$STATE_ROOT/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/guide-computer-graphics-prepare.XXXXXX")"
SOURCE_BEFORE="$TEMP_ROOT/source-before.json"
SOURCE_AFTER="$TEMP_ROOT/source-after.json"

cleanup() {
  rm -rf -- "$TEMP_ROOT"
}
trap cleanup EXIT HUP INT TERM

die() {
  printf '[prepare] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "필수 명령이 없습니다: $1"
}

for command_name in git python3 cmake c++; do
  require_command "$command_name"
done

cd "$ROOT"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die 'Git 저장소에서 실행해야 합니다.'
[[ "$(git branch --show-current)" == "$GUIDE_ID" ]] || die "브랜치가 $GUIDE_ID 가 아닙니다."
[[ ! -L "$STATE_ROOT" && ! -L "$STATE_DIR" ]] || die '.guide 상태 경로에 symbolic link를 사용할 수 없습니다.'
mkdir -p -- "$STATE_DIR"
[[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || die '.guide 상태 경로는 실제 directory여야 합니다.'

python3 scripts/repository_state.py --root "$ROOT" --output "$SOURCE_BEFORE" --reject-symlinks

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(f"Python 3.10 이상이 필요합니다: {sys.version}")
PY

python3 - <<'PY'
import re
import subprocess
text = subprocess.check_output(["cmake", "--version"], text=True).splitlines()[0]
match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
version = tuple(int(value or 0) for value in match.groups()) if match else (0, 0, 0)
if version < (3, 20, 0):
    raise SystemExit(f"CMake 3.20 이상이 필요합니다: {text}")
PY

c++ -x c++ -std=c++20 -Wall -Wextra -Werror -pedantic -o "$TEMP_ROOT/probe" - <<'CPP'
#include <array>
#include <span>
int main() {
  std::array<int, 3> values{1, 2, 3};
  return std::span<const int>(values).size() == 3 ? 0 : 1;
}
CPP
"$TEMP_ROOT/probe"

python3 - "$ROOT" "$MARKER" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import re

root = Path(sys.argv[1])
marker = Path(sys.argv[2])
sys.path.insert(0, str(root / "scripts"))
from source_fingerprint import fingerprint


def output(command: list[str]) -> str:
    result = subprocess.run(command, text=True, capture_output=True, timeout=10, check=False)
    return (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else ""


def optional_command(name: str, args: list[str]) -> dict[str, object]:
    path = shutil.which(name)
    if path is None:
        return {"available": False}
    return {"available": True, "path": path, "version": output([path, *args])}


def numeric_version(value: str | None) -> tuple[int, int, int]:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", value or "")
    if match is None:
        return (0, 0, 0)
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def index_hash() -> str:
    raw = subprocess.check_output(["git", "rev-parse", "--git-path", "index"], cwd=root, text=True).strip()
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    return hashlib.sha256(path.read_bytes()).hexdigest()


source_hash, source_count = fingerprint(root)
sdl = {"available": False, "version": None, "minimum": "3.4.10", "supported": False}
if shutil.which("pkg-config"):
    result = subprocess.run(["pkg-config", "--modversion", "sdl3"], text=True, capture_output=True, check=False)
    version = result.stdout.strip() if result.returncode == 0 else None
    sdl = {
        "available": result.returncode == 0,
        "version": version,
        "minimum": "3.4.10",
        "supported": result.returncode == 0 and numeric_version(version) >= (3, 4, 10),
        "diagnostic": result.stderr.strip() or None,
    }
payload = {
    "prepared_schema_version": 2,
    "guide": "computer-graphics",
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=root, text=True).strip(),
    "index_sha256": index_hash(),
    "source_sha256": source_hash,
    "source_file_count": source_count,
    "platform": platform.platform(),
    "required": {
        "python": platform.python_version(),
        "cmake": output(["cmake", "--version"]),
        "cxx": output(["c++", "--version"]),
    },
    "optional": {
        "sdl3": sdl,
        "renderdoccmd": optional_command("renderdoccmd", ["--version"]),
        "xcrun": optional_command("xcrun", ["--version"]),
    },
}
marker.parent.mkdir(parents=True, exist_ok=True)
descriptor, raw_path = tempfile.mkstemp(prefix=".prepared.", dir=marker.parent)
temporary = Path(raw_path)
try:
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, marker)
    directory_fd = os.open(marker.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
finally:
    if temporary.exists():
        temporary.unlink()
print(f"PREPARED {marker.relative_to(root)}")
print(f"SOURCE_SHA256 {source_hash}")
print(f"SDL3 {'FOUND ' + str(sdl.get('version')) if sdl.get('available') else 'NOT_FOUND'}")
PY

python3 scripts/repository_state.py --root "$ROOT" --output "$SOURCE_AFTER" --reject-symlinks
cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER" || die 'prepare가 source 파일·mode를 변경했습니다.'
python3 scripts/source_fingerprint.py --check-file "$MARKER" >/dev/null || die 'prepare marker source 지문이 일치하지 않습니다.'

printf '[prepare] PASS\n'
