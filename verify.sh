#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

GUIDE_ID="database-systems"
EXPECTED_POSTGRES_IMAGE="docker.io/library/postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_FILE="$ROOT/.guide/$GUIDE_ID/prepared.json"
RUN_ID="database-systems-$(date +%s)-$$-$RANDOM"
RUN_DIR=""
PASS_COUNT=0
FAIL_COUNT=0

preflight_die() { printf '[verify] ERROR: %s\n' "$*" >&2; exit 2; }

[[ -n "${VERIFY_LOG:-}" ]] || preflight_die "저장소 밖 절대 경로를 VERIFY_LOG로 지정하십시오."
[[ "$VERIFY_LOG" == /* ]] || preflight_die "VERIFY_LOG는 절대 경로여야 합니다: $VERIFY_LOG"
python3 - "$ROOT" "$VERIFY_LOG" <<'PY' || preflight_die "VERIFY_LOG는 저장소 밖이어야 합니다."
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve()
log = pathlib.Path(sys.argv[2])
parent = log.parent.resolve(strict=True)
resolved = parent / log.name
try:
    resolved.relative_to(root)
except ValueError:
    raise SystemExit(0)
raise SystemExit(1)
PY
[[ -w "$(dirname "$VERIFY_LOG")" ]] || preflight_die "VERIFY_LOG 디렉터리에 쓸 수 없습니다."
: > "$VERIFY_LOG"
exec > >(tee -a "$VERIFY_LOG") 2>&1

log() { printf '[verify] %s\n' "$*"; }

cleanup() {
    local status=$?
    trap - EXIT INT TERM HUP
    while IFS= read -r container; do
        [[ -n "$container" ]] && docker rm -f "$container" >/dev/null 2>&1 || true
    done < <(docker ps -aq --filter "label=guide.database-systems.verify=$RUN_ID" 2>/dev/null || true)
    for child in $(jobs -pr 2>/dev/null); do
        kill "$child" >/dev/null 2>&1 || true
    done
    [[ -z "$RUN_DIR" ]] || rm -rf -- "$RUN_DIR"
    printf '[verify] SUMMARY: pass=%d fail=%d skipped=0\n' "$PASS_COUNT" "$FAIL_COUNT"
    if [[ $status -eq 0 && $FAIL_COUNT -eq 0 ]]; then
        printf 'RESULT: PASS\n'
    else
        printf 'RESULT: FAIL\n'
    fi
    printf '[verify] LOG: %s\n' "$VERIFY_LOG"
    exit "$status"
}
trap cleanup EXIT INT TERM HUP

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    log "FAIL: $*"
    return 1
}

run_step() {
    local name="$1"
    shift
    printf '\n[verify] === %s ===\n' "$name"
    if "$@"; then
        PASS_COUNT=$((PASS_COUNT + 1))
        log "PASS: $name"
    else
        fail "$name"
    fi
}

for command in git python3 docker rsync; do
    command -v "$command" >/dev/null 2>&1 || preflight_die "$command 명령이 필요합니다."
done
[[ -f "$STATE_FILE" ]] || preflight_die "먼저 ./prepare.sh를 실행하십시오."

marker_error="$(python3 - "$STATE_FILE" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        payload = json.load(stream)
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    print(str(exc))
    raise SystemExit(1)
required_strings = {
    "guide_id",
    "head_commit",
    "source_fingerprint",
    "index_fingerprint",
    "python_version",
    "docker_version",
    "postgres_image",
    "postgres_image_id",
}
missing = sorted(key for key in required_strings if not isinstance(payload.get(key), str) or not payload[key])
if payload.get("schema_version") != 1 or missing:
    print("schema_version 또는 필수 field가 올바르지 않음: " + ", ".join(missing))
    raise SystemExit(1)
PY
)" || preflight_die "prepare marker가 손상되었습니다: $marker_error"

read_state() {
    python3 - "$STATE_FILE" "$1" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    payload = json.load(stream)
value = payload.get(sys.argv[2])
if not isinstance(value, (str, int)):
    raise SystemExit(1)
print(value)
PY
}

[[ "$(read_state guide_id)" == "$GUIDE_ID" ]] || preflight_die "prepare marker의 guide ID가 다릅니다."
[[ "$(read_state schema_version)" == "1" ]] || preflight_die "지원하지 않는 prepare marker입니다."
[[ "$(read_state postgres_image)" == "$EXPECTED_POSTGRES_IMAGE" ]] || preflight_die "prepare marker의 PostgreSQL digest가 다릅니다."
[[ "$(read_state head_commit)" == "$(git -C "$ROOT" rev-parse HEAD)" ]] || preflight_die "HEAD가 prepare 이후 바뀌었습니다. prepare를 다시 실행하십시오."
current_source="$(python3 "$ROOT/scripts/tree-fingerprint.py" "$ROOT")"
[[ "$current_source" == "$(read_state source_fingerprint)" ]] || preflight_die "source가 prepare 이후 바뀌었습니다. prepare를 다시 실행하십시오."

index_path="$(git -C "$ROOT" rev-parse --git-path index)"
[[ "$index_path" == /* ]] || index_path="$ROOT/$index_path"
current_index="$(python3 - "$index_path" <<'PY'
import hashlib
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
)"
[[ "$current_index" == "$(read_state index_fingerprint)" ]] || preflight_die "Git index가 prepare 이후 바뀌었습니다."

docker info >/dev/null 2>&1 || preflight_die "Docker daemon에 연결할 수 없습니다."
POSTGRES_IMAGE_ID="$(read_state postgres_image_id)"
docker image inspect "$POSTGRES_IMAGE_ID" >/dev/null 2>&1 || preflight_die "prepare에서 고정한 PostgreSQL 이미지가 없습니다."

RUN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-database-systems-verify.XXXXXX")"
case "$(cd "$RUN_DIR" && pwd -P)" in
    "$ROOT"|"$ROOT"/*) preflight_die "검증 임시 디렉터리가 저장소 안에 있습니다." ;;
esac
WORK_ROOT="$RUN_DIR/repo"
mkdir -p "$WORK_ROOT/.guide/$GUIDE_ID"
rsync -a --exclude=.git --exclude=.guide "$ROOT/" "$WORK_ROOT/"
cp "$STATE_FILE" "$WORK_ROOT/.guide/$GUIDE_ID/prepared.json"

export GUIDE_PREPARED_STATE="$WORK_ROOT/.guide/$GUIDE_ID/prepared.json"
export GUIDE_POSTGRES_IMAGE_ID="$POSTGRES_IMAGE_ID"
export GUIDE_VERIFY_RUN_ID="$RUN_ID"

cd "$WORK_ROOT"
run_step "저장소 구조·문서·버전 계약" python3 scripts/validate.py
run_step "validator mutant suite" python3 scripts/test-validator.py
run_step "workspace path/symlink safety" python3 scripts/test-workspace-tools.py
run_step "Shell 문법" bash -c 'while IFS= read -r -d "" script; do bash -n "$script"; done < <(find prepare.sh verify.sh scripts exercises -type f -name "*.sh" -print0)'
run_step "Python 예제" python3 scripts/run_examples.py
run_step "Python reference/skeleton 계약" python3 scripts/check-exercises.py
run_step "PostgreSQL reference/skeleton 및 query plan" ./scripts/run-postgres-exercises.sh

after_source="$(python3 "$ROOT/scripts/tree-fingerprint.py" "$ROOT")"
[[ "$after_source" == "$current_source" ]] || fail "verify가 원본 source tree를 변경했습니다."
after_index="$(python3 - "$index_path" <<'PY'
import hashlib
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
)"
[[ "$after_index" == "$current_index" ]] || fail "verify가 원본 Git index를 변경했습니다."

log "모든 검증을 통과했습니다."
