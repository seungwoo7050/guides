#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
RUN_ID="${GUIDE_VERIFY_RUN_ID:-database-systems-manual-$$-$RANDOM}"
STATE_FILE="${GUIDE_PREPARED_STATE:-$ROOT/.guide/database-systems/prepared.json}"
MODE="distribution"
WORKSPACE_REL=""
cases=(
  "exercises/01-relational-semantics-and-design/01-sql-semantics"
  "exercises/01-relational-semantics-and-design/02-schema-and-constraints"
  "exercises/03-transactions-and-recovery/01-postgres-isolation"
  "exercises/04-execution-and-optimization/02-query-plans-and-indexes"
  "exercises/04-execution-and-optimization/03-safe-migration-and-backfill"
  "exercises/05-capstones/01-application-database-review"
)

case "$#" in
  0) ;;
  2)
    [[ "$1" == "--workspace" ]] || {
        printf '사용법: %s [--workspace exercises/<경로>]\n' "$0" >&2
        exit 2
    }
    MODE="workspace"
    WORKSPACE_REL="$2"
    ;;
  *)
    printf '사용법: %s [--workspace exercises/<경로>]\n' "$0" >&2
    exit 2
    ;;
esac

if [[ "$MODE" == "workspace" ]]; then
    known=0
    for rel in "${cases[@]}"; do
        [[ "$rel" == "$WORKSPACE_REL" ]] && known=1
    done
    [[ $known -eq 1 && -d "$ROOT/$WORKSPACE_REL/workspace" ]] || {
        printf '[postgres] 지원하지 않는 PostgreSQL workspace: %s\n' "$WORKSPACE_REL" >&2
        exit 2
    }
fi

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
ACTIVE_CHILD=""
ACTIVE_OUTPUT=""
RUNTIME_MUTANT=""

cleanup() {
    docker rm -f "$container" >/dev/null 2>&1 || true
    [[ -z "$ACTIVE_OUTPUT" ]] || rm -f -- "$ACTIVE_OUTPUT"
    if [[ -n "$RUNTIME_MUTANT" && "$RUNTIME_MUTANT" == "$ROOT/exercises/05-capstones/01-application-database-review/workspace.tmp.runtime-index."* ]]; then
        rm -rf -- "$RUNTIME_MUTANT"
    fi
}

signal_exit() {
    local code="$1"
    trap - HUP INT TERM
    if [[ -n "$ACTIVE_CHILD" ]]; then
        kill -TERM "$ACTIVE_CHILD" >/dev/null 2>&1 || true
        # Removing the run-scoped container also unblocks any nested
        # docker-exec process before we escalate a stubborn child.
        cleanup
        for _ in {1..20}; do
            kill -0 "$ACTIVE_CHILD" >/dev/null 2>&1 || break
            sleep 0.05
        done
        kill -KILL "$ACTIVE_CHILD" >/dev/null 2>&1 || true
        wait "$ACTIVE_CHILD" 2>/dev/null || true
        ACTIVE_CHILD=""
    fi
    exit "$code"
}

trap cleanup EXIT
trap 'signal_exit 129' HUP
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM

printf '[postgres] 임시 PostgreSQL 18.4 시작\n'
docker run -d --pull=never --name "$container" \
    --label "guide.database-systems.verify=$RUN_ID" \
    -e POSTGRES_PASSWORD="$password" \
    -e POSTGRES_USER=guide \
    -e POSTGRES_DB=postgres \
    "$image_id" >/dev/null

ready=0
for ((attempt = 1; attempt <= 60; attempt++)); do
    # The official image briefly exposes its temporary init server before it
    # shuts that server down and starts the final postmaster.  A successful
    # SELECT alone can therefore race with the hand-off.  Require the explicit
    # init-complete marker as well as a query against the final server.
    if docker logs "$container" 2>&1 \
        | grep -Fq 'PostgreSQL init process complete; ready for start up.' \
        && docker exec "$container" psql -v ON_ERROR_STOP=1 -U guide -d postgres \
        -Atqc 'SELECT 1' 2>/dev/null | grep -qx 1; then
        ready=1
        break
    fi
    sleep 1
done
if [[ $ready -ne 1 ]]; then
    docker logs "$container" >&2
    exit 1
fi

designated_contract() {
    local rel="$1"
    case "$rel" in
      exercises/01-relational-semantics-and-design/01-sql-semantics)
        expected_status=3
        expected_error='q01 mismatch: <NULL>'
        semantic_token='GUIDE_SEMANTIC:sql-three-valued-logic'
        ;;
      exercises/01-relational-semantics-and-design/02-schema-and-constraints)
        expected_status=3
        expected_error='case-insensitive duplicate email was accepted'
        semantic_token='GUIDE_SEMANTIC:schema-email-constraint'
        ;;
      exercises/03-transactions-and-recovery/01-postgres-isolation)
        expected_status=1
        expected_error='inventory: expected one success, got 2'
        semantic_token='GUIDE_SEMANTIC:isolation-lost-update'
        ;;
      exercises/04-execution-and-optimization/02-query-plans-and-indexes)
        expected_status=1
        expected_error='relation "events_tenant_created_id_idx" does not exist'
        semantic_token='GUIDE_SEMANTIC:query-plan-index-contract'
        ;;
      exercises/04-execution-and-optimization/03-safe-migration-and-backfill)
        expected_status=3
        expected_error='column "status" of relation "orders" contains null values'
        semantic_token='GUIDE_SEMANTIC:migration-backfill-order'
        ;;
      exercises/05-capstones/01-application-database-review)
        expected_status=3
        expected_error='column "priority" of relation "tickets" already exists'
        semantic_token='GUIDE_SEMANTIC:capstone-idempotent-migration'
        ;;
      *) return 1 ;;
    esac
}

run_case() {
    local rel="$1" implementation="$2" expected="$3"
    local safe db status output expected_status expected_error semantic_token
    safe="${rel//\//_}"
    safe="${safe//-/_}"
    db="${safe}_${implementation}_${suffix}"
    db="${db:0:60}"
    docker exec "$container" createdb -U guide "$db"
    output="$(mktemp "${TMPDIR:-/tmp}/guide-db-postgres-case.XXXXXX")"
    ACTIVE_OUTPUT="$output"
    "$ROOT/$rel/tests/verify.sh" "$container" "$db" "$implementation" >"$output" 2>&1 &
    ACTIVE_CHILD=$!
    if wait "$ACTIVE_CHILD"; then
        status=0
    else
        status=$?
    fi
    ACTIVE_CHILD=""
    cat "$output"
    docker exec "$container" dropdb -U guide --if-exists "$db" >/dev/null
    if [[ "$expected" == pass && $status -ne 0 ]]; then
        if [[ "$implementation" == workspace ]] \
            && designated_contract "$rel" \
            && [[ $status -eq $expected_status ]] \
            && grep -Fq "$expected_error" "$output"; then
            printf '[FAIL] learner workspace designated start-state: %s (%s)\n' \
                "$rel" "$semantic_token" >&2
        else
            printf '[FAIL] PostgreSQL %s: %s\n' "$implementation" "$rel" >&2
        fi
        rm -f -- "$output"
        ACTIVE_OUTPUT=""
        return 1
    fi
    if [[ "$expected" == fail && $status -eq 0 ]]; then
        rm -f -- "$output"
        ACTIVE_OUTPUT=""
        printf '[FAIL] PostgreSQL skeleton이 통과함: %s\n' "$rel" >&2
        return 1
    fi
    if [[ "$expected" == fail ]]; then
        if ! designated_contract "$rel"; then
            rm -f -- "$output"
            ACTIVE_OUTPUT=""
            printf '[FAIL] 지정된 PostgreSQL skeleton 계약 없음: %s\n' "$rel" >&2
            return 1
        fi
        if [[ $status -ne $expected_status ]] || ! grep -Fq "$expected_error" "$output"; then
            rm -f -- "$output"
            ACTIVE_OUTPUT=""
            printf '[FAIL] PostgreSQL skeleton이 지정된 semantic failure와 다름: %s (status=%s, expected=%s)\n' \
                "$rel" "$status" "$expected_status" >&2
            return 1
        fi
        if grep -Eqi 'syntax error|connection .*failed|could not connect|no such container|command not found|permission denied' "$output"; then
            rm -f -- "$output"
            ACTIVE_OUTPUT=""
            printf '[FAIL] PostgreSQL skeleton infrastructure/setup failure: %s\n' "$rel" >&2
            return 1
        fi
        printf '[PASS] PostgreSQL designated semantic failure: %s (%s)\n' "$rel" "$semantic_token"
    fi
    rm -f -- "$output"
    ACTIVE_OUTPUT=""
    printf '[PASS] PostgreSQL %s (%s expected)\n' "$rel" "$expected"
}

run_capstone_index_runtime_mutant() {
    local rel base implementation db output status
    rel="exercises/05-capstones/01-application-database-review"
    base="$ROOT/$rel"
    RUNTIME_MUTANT="$(mktemp -d "$base/workspace.tmp.runtime-index.XXXXXX")"
    implementation="$(basename "$RUNTIME_MUTANT")"
    cp "$base/reference/schema.sql" "$RUNTIME_MUTANT/schema.sql"
    cp "$base/reference/migration.sql" "$RUNTIME_MUTANT/migration.sql"
    cp "$base/reference/queries.sql" "$RUNTIME_MUTANT/queries.sql"
    cp "$base/reference/indexes.sql" "$RUNTIME_MUTANT/indexes.sql"
    cp "$base/reference/concurrency-review.md" "$RUNTIME_MUTANT/concurrency-review.md"
    python3 - "$RUNTIME_MUTANT/indexes.sql" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = "ON tickets(org_id, assignee_id, priority DESC, created_at, id)"
new = "ON tickets(org_id, assignee_id, priority, created_at, id)"
if old not in text:
    raise SystemExit("runtime mutant target missing")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
PY

    db="capstone_index_mutant_${suffix}"
    db="${db:0:60}"
    docker exec "$container" createdb -U guide "$db"
    output="$(mktemp "${TMPDIR:-/tmp}/guide-db-runtime-mutant.XXXXXX")"
    ACTIVE_OUTPUT="$output"
    "$base/tests/verify.sh" "$container" "$db" "$implementation" >"$output" 2>&1 &
    ACTIVE_CHILD=$!
    if wait "$ACTIVE_CHILD"; then
        status=0
    else
        status=$?
    fi
    ACTIVE_CHILD=""
    docker exec "$container" dropdb -U guide --if-exists "$db" >/dev/null
    if [[ $status -eq 0 ]] || ! grep -Fq 'queue index definition mismatch' "$output"; then
        cat "$output" >&2
        rm -f -- "$output"
        ACTIVE_OUTPUT=""
        printf '[FAIL] capstone runtime index mutant was not rejected precisely\n' >&2
        return 1
    fi
    rm -f -- "$output"
    ACTIVE_OUTPUT=""
    rm -rf -- "$RUNTIME_MUTANT"
    RUNTIME_MUTANT=""
    printf '[PASS] capstone runtime mutant: wrong queue key order rejected by shared SQL/plan tests\n'
}

if [[ "$MODE" == "workspace" ]]; then
    run_case "$WORKSPACE_REL" workspace pass
else
    for rel in "${cases[@]}"; do
        run_case "$rel" reference pass
        run_case "$rel" skeleton fail
    done
    run_capstone_index_runtime_mutant
fi
