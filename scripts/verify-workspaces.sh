#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SLUGS=(
  application-boundaries
  security-boundaries
  transaction-locking
  idempotency-outbox
  kafka-avro-contract
  resilient-http-client
  single-service-capstone
)

cleanup() {
  [[ ! -L "$ROOT_DIR/.workspace" ]] || return 0
  rm -rf -- "$ROOT_DIR/.workspace"
}
trap cleanup EXIT

[[ "$(pwd -P)" == "$ROOT_DIR" ]] || {
  printf '저장소 루트에서 실행해야 합니다.\n' >&2
  exit 2
}
[[ ! -e "$ROOT_DIR/.workspace" && ! -L "$ROOT_DIR/.workspace" ]] || {
  printf 'workspace 검증 시작 전에 .workspace가 없어야 합니다.\n' >&2
  exit 1
}

for slug in "${SLUGS[@]}"; do
  "$ROOT_DIR/scripts/new-workspace.sh" "$slug" >/dev/null
  python3 - "$ROOT_DIR" "$slug" <<'PY'
import shutil
import sys
from pathlib import Path

root = Path(sys.argv[1])
slug = sys.argv[2]
source = root / "exercises" / slug / "reference/src/main"
destination = root / ".workspace" / slug / "src/main"
if destination.is_symlink() or destination.parents[1] != root / ".workspace" / slug:
    raise SystemExit("workspace main 경로가 안전하지 않습니다.")
shutil.rmtree(destination)
shutil.copytree(source, destination, symlinks=False, copy_function=shutil.copy2)
PY
  "$ROOT_DIR/scripts/check-workspace.sh" "$slug"
  printf '[PASS] %s workspace 수정본이 canonical 공개 tests 통과\n' "$slug"
done
