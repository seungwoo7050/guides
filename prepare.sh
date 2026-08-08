#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

GUIDE_ID="database-systems"
POSTGRES_IMAGE="docker.io/library/postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
STATE_FILE="$STATE_DIR/prepared.json"

log() { printf '[prepare] %s\n' "$*"; }
die() { printf '[prepare] ERROR: %s\n' "$*" >&2; exit 1; }

require_command() {
    command -v "$1" >/dev/null 2>&1 || die "$1 명령이 필요합니다."
}

index_fingerprint() {
    local index_path
    index_path="$(git -C "$ROOT" rev-parse --git-path index)"
    if [[ "$index_path" != /* ]]; then
        index_path="$ROOT/$index_path"
    fi
    python3 - "$index_path" <<'PY'
import hashlib
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
}

cd "$ROOT"
for command in git python3 docker; do
    require_command "$command"
done

python3 - <<'PY' || die "Python 3.11 이상이 필요합니다."
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY

top_level="$(git rev-parse --show-toplevel 2>/dev/null)" || die "Git 저장소에서 실행해야 합니다."
[[ "$(cd "$top_level" && pwd -P)" == "$ROOT" ]] || die "저장소 루트에서 실행해야 합니다."
[[ -f docs/00-roadmap.md ]] || die "가이드 구조가 불완전합니다: docs/00-roadmap.md"

before_source="$(python3 scripts/tree-fingerprint.py "$ROOT")"
before_index="$(index_fingerprint)"

docker info >/dev/null 2>&1 || die "Docker daemon에 연결할 수 없습니다."
log "PostgreSQL 18.4 이미지 준비"
docker pull "$POSTGRES_IMAGE" >/dev/null
image_id="$(docker image inspect --format '{{.Id}}' "$POSTGRES_IMAGE")"
[[ "$image_id" == sha256:* ]] || die "PostgreSQL image ID를 확인하지 못했습니다."

after_source="$(python3 scripts/tree-fingerprint.py "$ROOT")"
after_index="$(index_fingerprint)"
[[ "$before_source" == "$after_source" ]] || die "prepare가 source tree를 변경했습니다."
[[ "$before_index" == "$after_index" ]] || die "prepare가 Git index를 변경했습니다."

mkdir -p "$STATE_DIR"
state_tmp="$STATE_DIR/.prepared.json.$$"
trap 'rm -f "$state_tmp"' EXIT INT TERM HUP
GUIDE_ID="$GUIDE_ID" \
POSTGRES_IMAGE="$POSTGRES_IMAGE" \
POSTGRES_IMAGE_ID="$image_id" \
SOURCE_FINGERPRINT="$after_source" \
INDEX_FINGERPRINT="$after_index" \
HEAD_COMMIT="$(git rev-parse HEAD)" \
DOCKER_VERSION="$(docker version --format '{{.Server.Version}}')" \
python3 - "$state_tmp" <<'PY'
import json
import os
import pathlib
import platform
import sys

target = pathlib.Path(sys.argv[1])
payload = {
    "schema_version": 1,
    "guide_id": os.environ["GUIDE_ID"],
    "head_commit": os.environ["HEAD_COMMIT"],
    "source_fingerprint": os.environ["SOURCE_FINGERPRINT"],
    "index_fingerprint": os.environ["INDEX_FINGERPRINT"],
    "python_version": platform.python_version(),
    "docker_version": os.environ["DOCKER_VERSION"],
    "postgres_image": os.environ["POSTGRES_IMAGE"],
    "postgres_image_id": os.environ["POSTGRES_IMAGE_ID"],
}
target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
chmod 600 "$state_tmp"
mv -f "$state_tmp" "$STATE_FILE"
trap - EXIT INT TERM HUP

log "준비 상태: $STATE_FILE"
printf 'PREPARE RESULT: PASS\n'
