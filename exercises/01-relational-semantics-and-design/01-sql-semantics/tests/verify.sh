#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 CONTAINER DATABASE IMPLEMENTATION" >&2; exit 2; }
container="$1"; database="$2"; implementation="$3"
root="/guide/exercises/01-relational-semantics-and-design/01-sql-semantics"
psql=(docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database")
"${psql[@]}" < "$root/schema.sql"
"${psql[@]}" < "$root/seed.sql"
"${psql[@]}" < "$root/$implementation/answers.sql"
"${psql[@]}" < "$root/tests/verify.sql"
