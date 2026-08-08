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

indexes="$(psql_cmd "SELECT indexname FROM pg_indexes WHERE schemaname='public' ORDER BY indexname;")"
grep -qx 'tickets_project_open_created_idx' <<<"$indexes" || { echo 'backlog index missing' >&2; exit 1; }
grep -qx 'tickets_assignee_queue_idx' <<<"$indexes" || { echo 'queue index missing' >&2; exit 1; }
