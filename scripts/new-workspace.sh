#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MANIFEST="$ROOT/scripts/exercises.txt"
[[ $# -eq 1 ]] || { printf '사용법: %s exercises/<경로>\n' "$0" >&2; exit 2; }
requested="$1"

python3 - "$ROOT" "$MANIFEST" "$requested" <<'PY'
import os
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1]).resolve()
manifest = pathlib.Path(sys.argv[2])
requested = sys.argv[3]
allowed = {line.strip() for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()}
if requested not in allowed:
    raise SystemExit(f"manifest에 없는 exercise 경로입니다: {requested}")
base = root / requested
try:
    resolved = base.resolve(strict=True)
    resolved.relative_to(root / "exercises")
except (FileNotFoundError, ValueError) as exc:
    raise SystemExit(f"안전하지 않은 exercise 경로입니다: {requested}") from exc
skeleton = base / "skeleton"
if skeleton.is_symlink() or not skeleton.is_dir():
    raise SystemExit(f"정상적인 skeleton 디렉터리가 아닙니다: {requested}")
for dirpath, dirnames, filenames in os.walk(skeleton, followlinks=False):
    for name in [*dirnames, *filenames]:
        path = pathlib.Path(dirpath) / name
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise SystemExit(f"skeleton의 symlink는 허용하지 않습니다: {path.relative_to(root)}")
        if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise SystemExit(f"skeleton의 특수 파일은 허용하지 않습니다: {path.relative_to(root)}")
workspace = base / "workspace"
if os.path.lexists(workspace):
    raise SystemExit(f"workspace가 이미 있습니다: {requested}/workspace")
PY

base="$ROOT/$requested"
temporary="$base/workspace.tmp.$$"
trap 'rm -rf -- "$temporary"' EXIT INT TERM HUP
cp -R "$base/skeleton" "$temporary"
mv "$temporary" "$base/workspace"
trap - EXIT INT TERM HUP
printf '생성됨: %s/workspace\n' "$requested"
printf '초기 semantic failure 확인: ./scripts/check-workspace.sh %s\n' "$requested"
