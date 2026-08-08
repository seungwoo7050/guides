#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 CONTAINER DATABASE IMPLEMENTATION" >&2; exit 2; }
container="$1"; database="$2"; implementation="$3"
root="/guide/exercises/04-execution-and-optimization/02-query-plans-and-indexes"
psql_stdin() { docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database"; }
psql_cmd() { docker exec "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database" -Atq -c "$1"; }

psql_stdin < "$root/schema.sql"
psql_stdin < "$root/seed.sql"
psql_stdin < "$root/$implementation/indexes.sql"
psql_cmd "ANALYZE events; ANALYZE jobs;" >/dev/null

events_def="$(psql_cmd "SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indexrelid='events_tenant_created_id_idx'::regclass;")"
[[ "$events_def" == *"(tenant_id, created_at DESC, id DESC) INCLUDE (kind, payload)"* ]] || {
    printf 'events index contract mismatch: %s\n' "$events_def" >&2
    exit 1
}

jobs_def="$(psql_cmd "SELECT pg_get_indexdef(indexrelid) FROM pg_index WHERE indexrelid='jobs_pending_schedule_idx'::regclass;")"
[[ "$jobs_def" == *"(scheduled_at, id) INCLUDE (payload)"* ]] || {
    printf 'jobs index key/include mismatch: %s\n' "$jobs_def" >&2
    exit 1
}
[[ "$jobs_def" == *"WHERE (status = 'PENDING'::text)"* ]] || {
    printf 'jobs partial predicate mismatch: %s\n' "$jobs_def" >&2
    exit 1
}

plan_events="$(psql_cmd "SET enable_seqscan=off; EXPLAIN (COSTS OFF) SELECT id, created_at, kind, payload FROM events WHERE tenant_id=7 AND created_at <= '2025-01-03' ORDER BY created_at DESC, id DESC LIMIT 20;")"
grep -q 'events_tenant_created_id_idx' <<<"$plan_events" || { printf '%s\n' "$plan_events" >&2; exit 1; }
grep -Eq 'Index Only Scan|Index Scan' <<<"$plan_events" || { printf '%s\n' "$plan_events" >&2; exit 1; }

plan_jobs="$(psql_cmd "SET enable_seqscan=off; EXPLAIN (COSTS OFF) SELECT id, scheduled_at, payload FROM jobs WHERE status='PENDING' AND scheduled_at <= '2025-03-01' ORDER BY scheduled_at, id LIMIT 50;")"
grep -q 'jobs_pending_schedule_idx' <<<"$plan_jobs" || { printf '%s\n' "$plan_jobs" >&2; exit 1; }

actual_ids="$(psql_cmd "SELECT string_agg(id::text, ',' ORDER BY created_at DESC, id DESC) FROM (SELECT id, created_at FROM events WHERE tenant_id=7 AND created_at <= '2025-01-03' ORDER BY created_at DESC, id DESC LIMIT 20) q;")"
expected_ids='99956,99906,99856,99806,99756,99706,99656,99606,99556,99506,99456,99406,99356,99306,99256,99206,99156,99106,99056,99006'
[[ "$actual_ids" == "$expected_ids" ]] || {
    printf 'event ordering/result mismatch\nexpected=%s\nactual=%s\n' "$expected_ids" "$actual_ids" >&2
    exit 1
}
