#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MANIFEST="$ROOT/scripts/exercises.txt"
[[ $# -eq 1 ]] || { printf '사용법: %s exercises/<경로>\n' "$0" >&2; exit 2; }

python3 - "$ROOT" "$MANIFEST" "$1" <<'PY'
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
skeleton = base / "skeleton"
workspace = base / "workspace"
if workspace.is_symlink() or not workspace.is_dir():
    raise SystemExit(f"정상적인 workspace가 아닙니다: {requested}/workspace")
try:
    workspace.resolve(strict=True).relative_to(root / "exercises")
except (FileNotFoundError, ValueError) as exc:
    raise SystemExit(f"workspace가 exercise 경계를 벗어났습니다: {requested}") from exc

def inspect_tree(tree: pathlib.Path) -> set[str]:
    regular: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(tree, followlinks=False):
        for name in [*dirnames, *filenames]:
            path = pathlib.Path(dirpath) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise SystemExit(f"symlink는 허용하지 않습니다: {path.relative_to(root)}")
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise SystemExit(f"특수 파일은 허용하지 않습니다: {path.relative_to(root)}")
            if stat.S_ISREG(mode):
                regular.add(path.relative_to(tree).as_posix())
    return regular

required = inspect_tree(skeleton)
actual = inspect_tree(workspace)
missing = sorted(required - actual)
if missing:
    raise SystemExit("workspace 필수 파일 누락: " + ", ".join(missing))
print(f"[PASS] workspace: {requested} ({len(actual)} files)")
PY
