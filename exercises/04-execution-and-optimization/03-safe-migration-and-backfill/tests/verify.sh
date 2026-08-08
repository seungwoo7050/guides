#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 CONTAINER DATABASE IMPLEMENTATION" >&2; exit 2; }
container="$1"; database="$2"; implementation="$3"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
psql=(docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database")
"${psql[@]}" < "$root/initial.sql"
"${psql[@]}" < "$root/$implementation/migration.sql"
# 준비·backfill 단계는 중단 뒤 재실행 가능한 계약을 가진다.
"${psql[@]}" < "$root/$implementation/migration.sql"
"${psql[@]}" < "$root/tests/verify.sql"
