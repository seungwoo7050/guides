#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
PROJECT="$ROOT/exercises/08-renderer-capstone/project"
SOURCE="$PROJECT/starter"
TARGET="$PROJECT/workspace"

die() {
  printf '[workspace] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "$#" -eq 0 ]] || die '이 명령은 인자를 받지 않습니다.'
[[ -d "$SOURCE" && ! -L "$SOURCE" ]] || die "starter가 없습니다: $SOURCE"
[[ -d "$PROJECT" && ! -L "$PROJECT" ]] || die 'project 경로는 실제 directory여야 합니다.'
[[ ! -e "$TARGET" && ! -L "$TARGET" ]] || die '기존 workspace를 덮어쓰지 않습니다. 먼저 백업한 뒤 직접 정리하십시오.'

python3 - "$SOURCE" "$TARGET" <<'PY'
from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
import tempfile

source = Path(sys.argv[1]).resolve(strict=True)
target = Path(sys.argv[2])
parent = target.parent.resolve(strict=True)
if target.parent != parent or target.name != "workspace":
    raise SystemExit("workspace target validation failed")
temporary = Path(tempfile.mkdtemp(prefix=".workspace.", dir=parent))
try:
    shutil.rmtree(temporary)
    shutil.copytree(source, temporary, symlinks=False)
    os.replace(temporary, target)
except BaseException:
    if temporary.exists():
        shutil.rmtree(temporary)
    raise
PY

printf '[workspace] CREATED %s\n' "$TARGET"
printf '%s\n' '다음 단계:'
printf '%s\n' '  python3 exercises/check.py --impl workspace --stage 01-transform-trace --expect pass --gpu off'
printf '%s\n' 'workspace는 Git 추적 대상이 아니며 이 스크립트는 자동 삭제하거나 재생성하지 않습니다.'
