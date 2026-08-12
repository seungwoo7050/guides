#!/bin/sh
set -eu
# [Implementation 8] transaction-consistent logical snapshot의 host-side owner입니다.
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$base_dir/backups"
password=$(cat "$base_dir/secrets/db_password.txt")
docker compose -f "$base_dir/compose.yaml" exec -T db \
    mariadb-dump -uappuser -p"$password" --single-transaction appdb \
    > "$base_dir/backups/appdb.sql"
echo "$base_dir/backups/appdb.sql"
