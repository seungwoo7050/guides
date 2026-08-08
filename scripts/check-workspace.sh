#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
MANIFEST="$ROOT/scripts/workspaces.txt"

[[ $# -eq 1 ]] || {
  printf '사용법: %s exercises/<경로>\n' "$0" >&2
  exit 2
}

workspace=$(python3 - "$ROOT" "$MANIFEST" "$1" <<'PY'
import os
import pathlib
import stat
import sys

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


def inspect_tree(tree: pathlib.Path) -> set[str]:
    regular: set[str] = set()
    for directory, dirnames, filenames in os.walk(tree, followlinks=False):
        for name in [*dirnames, *filenames]:
            path = pathlib.Path(directory) / name
            mode = path.lstat().st_mode
            relative = path.relative_to(root)
            if stat.S_ISLNK(mode):
                fail(f"symlink는 허용하지 않습니다: {relative}")
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                fail(f"특수 파일은 허용하지 않습니다: {relative}")
            if stat.S_ISREG(mode):
                regular.add(path.relative_to(tree).as_posix())
    return regular


mappings = load_manifest()
name = mappings.get(requested)
if name is None:
    fail(f"manifest에 없는 exercise 경로입니다: {requested}")
exercise = root / requested
skeleton = exercise / "skeleton"
workspace_root = root / ".workspace"
workspace = workspace_root / name
if workspace_root.is_symlink() or not workspace_root.is_dir():
    fail("정상적인 .workspace 디렉터리가 아닙니다.")
if workspace.is_symlink() or not workspace.is_dir():
    fail(f"정상적인 learner workspace가 아닙니다: .workspace/{name}")
try:
    exercise.resolve(strict=True).relative_to(root / "exercises")
    workspace.resolve(strict=True).relative_to(workspace_root.resolve(strict=True))
except (FileNotFoundError, ValueError) as error:
    fail(f"workspace가 저장소 경계를 벗어났습니다: {error}")

required = inspect_tree(skeleton)
actual = inspect_tree(workspace)
missing = sorted(required - actual)
if missing:
    fail("workspace 필수 파일 누락: " + ", ".join(missing))

for relative in sorted(path for path in required if path.startswith("src/test/")):
    if (skeleton / relative).read_bytes() != (workspace / relative).read_bytes():
        fail(f"공개 테스트를 변경했습니다: .workspace/{name}/{relative}")

skeleton_pom = (skeleton / "pom.xml").read_text(encoding="utf-8")
expected_pom = skeleton_pom.replace(
    "<relativePath>../../../../pom.xml</relativePath>",
    "<relativePath>../../pom.xml</relativePath>",
)
if expected_pom == skeleton_pom or (workspace / "pom.xml").read_text(encoding="utf-8") != expected_pom:
    fail(f"workspace POM 계약을 변경했습니다: .workspace/{name}/pom.xml")

print(workspace)
PY
)

printf '[workspace] 공용 테스트 검증: %s\n' "$1"
"$ROOT/scripts/mvn-guide.sh" -f "$workspace/pom.xml" test
printf '[PASS] learner workspace: %s\n' "$1"
