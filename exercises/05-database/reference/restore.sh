#!/bin/sh
set -eu
# [Implementation 9] 명시한 backup만 target DB에 적용해 restore 경계를 분리합니다.
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
backup="${1:-$base_dir/backups/appdb.sql}"
[ -r "$backup" ] || { echo "백업 파일을 읽을 수 없습니다: $backup" >&2; exit 1; }
password=$(cat "$base_dir/secrets/db_password.txt")
docker compose -f "$base_dir/compose.yaml" exec -T db \
    mariadb -uappuser -p"$password" appdb < "$backup"
