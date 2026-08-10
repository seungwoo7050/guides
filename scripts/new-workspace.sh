#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
PYTHON=${PYTHON:-python3}
CREATED=
DEST_ABS=

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

cleanup() {
  status=$?
  trap - EXIT HUP INT TERM
  if test "$status" -ne 0 && test -n "$CREATED" && test -n "$DEST_ABS" && test -d "$DEST_ABS" && test ! -L "$DEST_ABS"; then
    rm -rf -- "$DEST_ABS"
  fi
  exit "$status"
}
trap cleanup EXIT HUP INT TERM

if test "$#" -lt 1 || test "$#" -gt 2; then
  echo "usage: $0 <exercise-or-capstone-directory> [destination]" >&2
  exit 2
fi
command -v "$PYTHON" >/dev/null 2>&1 || fail "Python이 없습니다: $PYTHON"

SOURCE_INFO=$(
  "$PYTHON" - "$ROOT" "$1" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
raw = sys.argv[2]
if "\n" in raw or "\r" in raw:
    raise SystemExit("ERROR: source path contains a newline")
candidate = Path(raw) if Path(raw).is_absolute() else root / raw
lexical = Path(os.path.abspath(candidate))
try:
    resolved = lexical.resolve(strict=True)
except OSError as error:
    raise SystemExit(f"ERROR: source directory does not exist: {raw}: {error}")
if lexical != resolved:
    raise SystemExit("ERROR: source path must not traverse symlink aliases")
try:
    relative = lexical.relative_to(root)
except ValueError:
    raise SystemExit("ERROR: source must stay under the guide root")
if len(relative.parts) != 2 or relative.parts[0] not in {"exercises", "capstone"}:
    raise SystemExit("ERROR: source must be a direct child of exercises/ or capstone/")
if not lexical.is_dir() or lexical.is_symlink() or not (lexical / "README.md").is_file():
    raise SystemExit("ERROR: source is not a real learning-unit directory with README.md")
starter = lexical / "starter"
if not starter.is_dir() or starter.is_symlink():
    raise SystemExit("ERROR: source has no safe starter directory")
for path in starter.rglob("*"):
    if path.is_symlink():
        raise SystemExit(f"ERROR: starter contains a symlink: {path.relative_to(starter)}")
if not any(path.is_file() for path in starter.rglob("*")):
    raise SystemExit("ERROR: starter directory is empty")
print(lexical)
print(starter)
PY
) || exit $?
SOURCE_ABS=$(printf '%s\n' "$SOURCE_INFO" | sed -n '1p')
STARTER=$(printf '%s\n' "$SOURCE_INFO" | sed -n '2p')

if test "$#" -eq 2; then
  DEST_INPUT=$2
else
  DEST_INPUT=$SOURCE_ABS/workspace
fi
DEST_ABS=$(
  "$PYTHON" - "$ROOT" "$DEST_INPUT" <<'PY'
import os
import sys
from pathlib import Path

root = Path(sys.argv[1])
raw = sys.argv[2]
if "\n" in raw or "\r" in raw:
    raise SystemExit("ERROR: destination path contains a newline")
candidate = Path(raw) if Path(raw).is_absolute() else root / raw
lexical = Path(os.path.abspath(candidate))
if os.path.lexists(lexical):
    raise SystemExit(f"ERROR: destination already exists: {lexical}")
parent = lexical.parent
try:
    resolved_parent = parent.resolve(strict=True)
except OSError as error:
    raise SystemExit(f"ERROR: destination parent must already exist: {parent}: {error}")
if parent != resolved_parent or parent.is_symlink():
    raise SystemExit("ERROR: destination parent must not traverse symlinks")
if not parent.is_dir():
    raise SystemExit(f"ERROR: destination parent is not a directory: {parent}")
print(lexical)
PY
) || exit $?

# mkdir is the ownership boundary: a concurrent creator makes this command fail,
# and no existing destination is copied into or removed.
mkdir -- "$DEST_ABS" || fail "destination was created concurrently: $DEST_ABS"
CREATED=1
cp -R "$STARTER"/. "$DEST_ABS"/ || fail "starter copy failed"

mkdir -p "$DEST_ABS/evidence"

if test ! -e "$DEST_ABS/README.md" && test ! -L "$DEST_ABS/README.md"; then
  SOURCE_REL=${SOURCE_ABS#"$ROOT"/}
  (set -C; cat > "$DEST_ABS/README.md" <<EOF
# 작업 공간

원본 과제: \`$SOURCE_REL\`

## 선택한 profile

- target/model:
- toolchain/version:
- source revision:

## 구현 범위

## 의도적 비범위

## 실행과 검증

## 확인하지 못한 항목
EOF
  ) || fail "README scaffold를 독점 생성할 수 없습니다."
fi

if test ! -e "$DEST_ABS/design.md" && test ! -L "$DEST_ABS/design.md"; then
  (set -C; cat > "$DEST_ABS/design.md" <<'EOF'
# 설계

## 상태와 소유자

## 입력 사건

## 불변식

## timeout, reset와 recovery

## 검증 계획
EOF
  ) || fail "design scaffold를 독점 생성할 수 없습니다."
fi

if test ! -e "$DEST_ABS/report.md" && test ! -L "$DEST_ABS/report.md"; then
  (set -C; cat > "$DEST_ABS/report.md" <<'EOF'
# 결과

## 실행한 검사

## raw evidence

## 결과와 반증

## 검증의 한계

## 다음 단계
EOF
  ) || fail "report scaffold를 독점 생성할 수 없습니다."
fi

CREATED=
echo "CREATED $DEST_ABS"
