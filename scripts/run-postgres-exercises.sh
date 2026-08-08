#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
RUN_ID="${GUIDE_VERIFY_RUN_ID:-database-systems-manual-$$-$RANDOM}"
STATE_FILE="${GUIDE_PREPARED_STATE:-$ROOT/.guide/database-systems/prepared.json}"
[[ -f "$STATE_FILE" ]] || { printf '[postgres] prepare 상태 없음: %s\n' "$STATE_FILE" >&2; exit 1; }

image_id="${GUIDE_POSTGRES_IMAGE_ID:-$(python3 - "$STATE_FILE" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    print(json.load(stream)["postgres_image_id"])
PY
)}"
docker image inspect "$image_id" >/dev/null 2>&1 || {
    printf '[postgres] 준비된 PostgreSQL 이미지가 없습니다: %s\n' "$image_id" >&2
    exit 1
}

suffix="${RANDOM}-$$"
container="guide-db-verify-$suffix"
password="guide_verify_$suffix"

cleanup() {
    docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM HUP

printf '[postgres] 임시 PostgreSQL 18.4 시작\n'
docker run -d --pull=never --name "$container" \
    --label "guide.database-systems.verify=$RUN_ID" \
    -e POSTGRES_PASSWORD="$password" \
    -e POSTGRES_USER=guide \
    -e POSTGRES_DB=postgres \
    "$image_id" >/dev/null

ready=0
for ((attempt = 1; attempt <= 60; attempt++)); do
    if docker exec "$container" pg_isready -U guide -d postgres >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
if [[ $ready -ne 1 ]]; then
    docker logs "$container" >&2
    exit 1
fi

cases=(
  "exercises/01-relational-semantics-and-design/01-sql-semantics"
  "exercises/01-relational-semantics-and-design/02-schema-and-constraints"
  "exercises/03-transactions-and-recovery/01-postgres-isolation"
  "exercises/04-execution-and-optimization/02-query-plans-and-indexes"
  "exercises/04-execution-and-optimization/03-safe-migration-and-backfill"
  "exercises/05-capstones/01-application-database-review"
)

run_case() {
    local rel="$1" implementation="$2" expected="$3"
    local safe db status
    safe="${rel//\//_}"
    safe="${safe//-/_}"
    db="${safe}_${implementation}_${suffix}"
    db="${db:0:60}"
    docker exec "$container" createdb -U guide "$db"
    set +e
    "$ROOT/$rel/tests/verify.sh" "$container" "$db" "$implementation"
    status=$?
    set -e
    docker exec "$container" dropdb -U guide --if-exists "$db" >/dev/null
    if [[ "$expected" == pass && $status -ne 0 ]]; then
        printf '[FAIL] PostgreSQL reference: %s\n' "$rel" >&2
        return 1
    fi
    if [[ "$expected" == fail && $status -eq 0 ]]; then
        printf '[FAIL] PostgreSQL skeleton이 통과함: %s\n' "$rel" >&2
        return 1
    fi
    printf '[PASS] PostgreSQL %s (%s expected)\n' "$rel" "$expected"
}

for rel in "${cases[@]}"; do
    run_case "$rel" reference pass
    run_case "$rel" skeleton fail
done
