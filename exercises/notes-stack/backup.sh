#!/bin/sh
set -eu

# [Implementation 10] Transaction-consistent logical backup
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
install -d -m 0700 "$base_dir/backups"
password=$(cat "$base_dir/secrets/db_password.txt")
target=${1:-$base_dir/backups/appdb.sql}
temporary="$target.tmp.$$"
trap 'rm -f "$temporary"' EXIT HUP INT TERM
docker compose -f "$base_dir/compose.yaml" exec -T db \
    mariadb-dump -uappuser -p"$password" --single-transaction --routines --triggers appdb \
    > "$temporary"
chmod 0600 "$temporary"
mv "$temporary" "$target"
trap - EXIT HUP INT TERM
printf '%s\n' "$target"
