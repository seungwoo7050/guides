#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
MANIFEST="$ROOT/scripts/exercises.txt"
[[ $# -eq 1 ]] || { printf '사용법: %s exercises/<경로>\n' "$0" >&2; exit 2; }
requested="$1"

workspace="$(python3 - "$ROOT" "$MANIFEST" "$requested" <<'PY'
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
print(workspace)
PY
)"

base="$ROOT/$requested"
if find "$base/tests" -maxdepth 1 -type f -name 'test_*.py' | grep -q .; then
    printf '[workspace] Python 공용 계약 검증: %s\n' "$requested"
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="$workspace" \
        python3 -m unittest discover -s "$base/tests" -v
elif [[ -x "$base/tests/verify.sh" ]]; then
    printf '[workspace] PostgreSQL 공용 계약 검증: %s\n' "$requested"
    "$ROOT/scripts/run-postgres-exercises.sh" --workspace "$requested"
else
    printf '실행할 공용 테스트를 찾지 못했습니다: %s\n' "$requested" >&2
    exit 2
fi

printf '[PASS] learner workspace: %s\n' "$requested"
