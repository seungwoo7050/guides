#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 CONTAINER DATABASE IMPLEMENTATION" >&2; exit 2; }
container="$1"; database="$2"; implementation="$3"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
psql_stdin() { docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database"; }
psql_cmd() { docker exec "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database" -Atq -c "$1"; }

psql_stdin < "$root/$implementation/schema.sql"
psql_stdin < "$root/seed.sql"
psql_stdin < "$root/$implementation/migration.sql"
psql_stdin < "$root/$implementation/migration.sql"
psql_stdin < "$root/$implementation/queries.sql"
psql_stdin < "$root/$implementation/queries.sql"
psql_stdin < "$root/$implementation/indexes.sql"
psql_stdin < "$root/$implementation/indexes.sql"
psql_stdin < "$root/tests/verify.sql"
psql_cmd "ANALYZE tickets;" >/dev/null

assert_index_definition() {
    local name="$1" expected="$2" label="$3" actual
    actual="$(psql_cmd "SELECT pg_get_indexdef('$name'::regclass);")"
    [[ "$actual" == "$expected" ]] || {
        printf '%s index definition mismatch\nexpected: %s\nactual:   %s\n' "$label" "$expected" "$actual" >&2
        exit 1
    }
}

assert_plan() {
    local name="$1" query="$2" label="$3" plan
    plan="$(psql_cmd "SET enable_seqscan=off; SET enable_bitmapscan=off; EXPLAIN (ANALYZE, COSTS OFF, TIMING OFF, SUMMARY OFF) $query")"
    grep -Eq "Index (Only )?Scan using $name" <<<"$plan" || {
        printf '%s plan did not use %s\n%s\n' "$label" "$name" "$plan" >&2
        exit 1
    }
    if grep -Eq '(^|[[:space:]])Sort([[:space:]]|$)' <<<"$plan"; then
        printf '%s plan contains an explicit Sort\n%s\n' "$label" "$plan" >&2
        exit 1
    fi
}

assert_index_definition \
    tickets_org_open_priority_created_idx \
    "CREATE INDEX tickets_org_open_priority_created_idx ON public.tickets USING btree (org_id, priority DESC, created_at DESC, id DESC) WHERE (status <> 'DONE'::text)" \
    'organization page'
assert_index_definition \
    tickets_assignee_queue_idx \
    "CREATE INDEX tickets_assignee_queue_idx ON public.tickets USING btree (org_id, assignee_id, priority DESC, created_at, id) WHERE ((status <> 'DONE'::text) AND (assignee_id IS NOT NULL))" \
    'queue'
assert_index_definition \
    tickets_project_open_created_idx \
    "CREATE INDEX tickets_project_open_created_idx ON public.tickets USING btree (org_id, project_id, created_at, id) WHERE (status <> 'DONE'::text)" \
    'backlog'

assert_plan tickets_org_open_priority_created_idx \
    "SELECT id, priority, created_at FROM tickets WHERE org_id=1 AND status <> 'DONE' AND (priority, created_at, id) < (4, TIMESTAMPTZ '2025-01-02 00:00:00+00', 101) ORDER BY priority DESC, created_at DESC, id DESC LIMIT 2;" \
    'organization page'
assert_plan tickets_assignee_queue_idx \
    "SELECT id, priority, created_at FROM tickets WHERE org_id=1 AND assignee_id=2 AND status <> 'DONE' ORDER BY priority DESC, created_at, id;" \
    'queue'
assert_plan tickets_project_open_created_idx \
    "SELECT count(*) FROM tickets WHERE org_id=1 AND project_id=10 AND status <> 'DONE';" \
    'backlog'

review="$root/$implementation/concurrency-review.md"
[[ -f "$review" ]] || { echo 'concurrency review artifact missing' >&2; exit 1; }
if grep -Fq '| 1 | 실행할 SQL | 실행 전 상태 | 기록 |' "$review"; then
    echo 'concurrency review remains scaffold' >&2
    exit 1
fi
for token in 'session A' 'session B' '허용' '금지' 'lock' 'application'; do
    grep -Fiq "$token" "$review" || {
        printf 'concurrency review evidence missing: %s\n' "$token" >&2
        exit 1
    }
done
sql_evidence_count="$(grep -Ec '`[^`]+`' "$review" || true)"
[[ "$sql_evidence_count" -ge 3 ]] || { echo 'concurrency review SQL evidence fewer than 3 lines' >&2; exit 1; }
