#!/bin/sh
set -eu

# [Implementation 5] Runtime secret ownership
: "${DB_HOST:?DB_HOST is required}"
: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD_FILE:?DB_PASSWORD_FILE is required}"
[ -r "$DB_PASSWORD_FILE" ] || { echo "DB_PASSWORD_FILE is not readable: $DB_PASSWORD_FILE" >&2; exit 1; }

runtime_secret_dir=/run/app-secrets
runtime_password_file="$runtime_secret_dir/db_password"
install -d -m 0750 -o root -g www-data "$runtime_secret_dir"
install -m 0440 -o root -g www-data "$DB_PASSWORD_FILE" "$runtime_password_file"
export DB_PASSWORD_FILE="$runtime_password_file"

# [Implementation 5-1] Bootstrap-to-FPM process handoff
php /opt/app/bootstrap.php
exec "$@"
