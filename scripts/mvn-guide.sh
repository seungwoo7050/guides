#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
MARKER="$ROOT_DIR/.guide/backend-spring-boot/prepared.json"

[[ -f "$MARKER" ]] || {
  printf '[FAIL] prepare marker가 없습니다. 먼저 ./prepare.sh를 실행하세요.\n' >&2
  exit 1
}

fingerprint="$(python3 "$ROOT_DIR/scripts/source_fingerprint.py" "$ROOT_DIR")"
values="$(python3 - "$MARKER" "$fingerprint" <<'PY'
import json
import sys
from pathlib import Path

marker = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if marker.get("guide_id") != "backend-spring-boot":
    raise SystemExit("prepare marker의 guide ID가 다릅니다.")
if marker.get("input_fingerprint") != sys.argv[2]:
    raise SystemExit("prepare marker가 현재 source와 맞지 않습니다. ./prepare.sh를 다시 실행하세요.")
home = Path(marker["maven_home"])
repository = Path(marker["maven_repository"])
if not home.is_dir() or not repository.is_dir():
    raise SystemExit("준비된 Maven cache가 없습니다. ./prepare.sh를 다시 실행하세요.")
print(f"{home}\t{repository}")
PY
)"
IFS=$'\t' read -r maven_home maven_repository <<<"$values"

exec env MAVEN_USER_HOME="$maven_home" \
  "$ROOT_DIR/mvnw" -B -ntp -o \
  -Dmaven.repo.local="$maven_repository" "$@"
