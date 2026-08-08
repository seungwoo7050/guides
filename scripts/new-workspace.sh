#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
MANIFEST="$ROOT/scripts/workspaces.txt"

[[ $# -eq 1 ]] || {
  printf '사용법: %s exercises/<경로>\n' "$0" >&2
  exit 2
}

python3 - "$ROOT" "$MANIFEST" "$1" <<'PY'
import os
import pathlib
import shutil
import stat
import sys
import tempfile

root = pathlib.Path(sys.argv[1]).resolve()
manifest_path = pathlib.Path(sys.argv[2])
requested = sys.argv[3]


def fail(message: str) -> None:
    raise SystemExit(message)


def load_manifest() -> dict[str, str]:
    mappings: dict[str, str] = {}
    for number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] in mappings:
            fail(f"잘못된 workspace manifest입니다: {manifest_path}:{number}")
        mappings[fields[0]] = fields[1]
    return mappings


def inspect_tree(tree: pathlib.Path) -> None:
    for directory, dirnames, filenames in os.walk(tree, followlinks=False):
        for name in [*dirnames, *filenames]:
            path = pathlib.Path(directory) / name
            mode = path.lstat().st_mode
            relative = path.relative_to(root)
            if stat.S_ISLNK(mode):
                fail(f"skeleton의 symlink는 허용하지 않습니다: {relative}")
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                fail(f"skeleton의 특수 파일은 허용하지 않습니다: {relative}")


mappings = load_manifest()
name = mappings.get(requested)
if name is None:
    fail(f"manifest에 없는 exercise 경로입니다: {requested}")
exercise = root / requested
try:
    exercise.resolve(strict=True).relative_to(root / "exercises")
except (FileNotFoundError, ValueError) as error:
    fail(f"안전하지 않은 exercise 경로입니다: {requested}: {error}")
skeleton = exercise / "skeleton"
if skeleton.is_symlink() or not skeleton.is_dir():
    fail(f"정상적인 skeleton 디렉터리가 아닙니다: {requested}")
inspect_tree(skeleton)

workspace_root = root / ".workspace"
if os.path.lexists(workspace_root):
    if workspace_root.is_symlink() or not workspace_root.is_dir():
        fail("정상적인 .workspace 디렉터리가 아닙니다.")
else:
    workspace_root.mkdir(mode=0o755)
try:
    workspace_root.resolve(strict=True).relative_to(root)
except (FileNotFoundError, ValueError) as error:
    fail(f".workspace가 저장소 경계를 벗어났습니다: {error}")

destination = workspace_root / name
if os.path.lexists(destination):
    fail(f"workspace가 이미 있습니다: .workspace/{name}")
temporary = pathlib.Path(tempfile.mkdtemp(prefix=f".{name}.tmp-", dir=workspace_root))
try:
    shutil.copytree(skeleton, temporary, dirs_exist_ok=True, symlinks=False)
    pom = temporary / "pom.xml"
    text = pom.read_text(encoding="utf-8")
    old = "<relativePath>../../../../pom.xml</relativePath>"
    new = "<relativePath>../../pom.xml</relativePath>"
    if text.count(old) != 1:
        fail(f"skeleton POM parent 경로 계약이 올바르지 않습니다: {requested}")
    pom.write_text(text.replace(old, new), encoding="utf-8")
    temporary.rename(destination)
except BaseException:
    shutil.rmtree(temporary, ignore_errors=True)
    raise

print(f"생성됨: .workspace/{name}")
print(f"초기 지정 실패 확인: ./scripts/check-workspace.sh {requested}")
PY
