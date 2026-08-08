#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 CONTAINER DATABASE IMPLEMENTATION" >&2; exit 2; }
container="$1"; database="$2"; implementation="$3"
root="/guide/exercises/01-relational-semantics-and-design/02-schema-and-constraints"
psql=(docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database")
"${psql[@]}" < "$root/$implementation/schema.sql"
"${psql[@]}" < "$root/tests/verify.sql"
