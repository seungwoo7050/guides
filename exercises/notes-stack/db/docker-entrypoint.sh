#!/bin/sh
set -eu

# [Implementation 2] Secret input and identifier validation
file_env() {
    var=$1
    file_var="${var}_FILE"
    default_value=${2:-}
    eval "value=\${$var:-}"
    eval "file_path=\${$file_var:-}"

    if [ -n "$value" ] && [ -n "$file_path" ]; then
        echo "$var and $file_var cannot both be set" >&2
        exit 1
    fi
    if [ -n "$file_path" ]; then
        [ -r "$file_path" ] || { echo "$file_var is not readable" >&2; exit 1; }
        value=$(cat "$file_path")
    elif [ -z "$value" ]; then
        value=$default_value
    fi
    export "$var=$value"
    unset "$file_var"
}

require_identifier() {
    label=$1
    value=$2
    case "$value" in
        ''|*[!A-Za-z0-9_]*)
            echo "$label may contain only letters, digits, and underscores" >&2
            exit 1
            ;;
    esac
}

sql_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"
}

file_env MARIADB_ROOT_PASSWORD
file_env MARIADB_PASSWORD
: "${MARIADB_ROOT_PASSWORD:?MARIADB_ROOT_PASSWORD is required}"
: "${MARIADB_DATABASE:?MARIADB_DATABASE is required}"
: "${MARIADB_USER:?MARIADB_USER is required}"
: "${MARIADB_PASSWORD:?MARIADB_PASSWORD is required}"
require_identifier MARIADB_DATABASE "$MARIADB_DATABASE"
require_identifier MARIADB_USER "$MARIADB_USER"

datadir=/var/lib/mysql
socket=/run/mysqld/mysqld.sock
install -d -m 0755 -o mysql -g mysql /run/mysqld "$datadir"

# [Implementation 2-1] First-run data directory initialization
if [ ! -d "$datadir/mysql" ]; then
    echo "initializing MariaDB data directory" >&2
    mariadb-install-db \
        --user=mysql \
        --datadir="$datadir" \
        --skip-test-db \
        --auth-root-authentication-method=socket >/dev/null

    # [Implementation 2-2] Isolated bootstrap server readiness
    mariadbd \
        --user=mysql \
        --datadir="$datadir" \
        --skip-networking \
        --socket="$socket" &
    temp_pid=$!
    cleanup_temp() {
        kill -TERM "$temp_pid" 2>/dev/null || true
        wait "$temp_pid" 2>/dev/null || true
    }
    trap cleanup_temp EXIT
    trap 'exit 129' HUP
    trap 'exit 130' INT
    trap 'exit 143' TERM

    ready=0
    counter=0
    while [ "$counter" -lt 60 ]; do
        if mariadb-admin --protocol=socket --socket="$socket" ping --silent >/dev/null 2>&1; then
            ready=1
            break
        fi
        sleep 1
        counter=$((counter + 1))
    done
    [ "$ready" -eq 1 ] || { echo "temporary MariaDB did not become ready" >&2; exit 1; }

    root_password=$(sql_escape "$MARIADB_ROOT_PASSWORD")
    app_password=$(sql_escape "$MARIADB_PASSWORD")

    # [Implementation 2-3] Database provisioning and final process handoff
    mariadb --protocol=socket --socket="$socket" -uroot <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${root_password}';
DROP DATABASE IF EXISTS test;
CREATE DATABASE IF NOT EXISTS \`${MARIADB_DATABASE}\`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${MARIADB_USER}'@'%' IDENTIFIED BY '${app_password}';
ALTER USER '${MARIADB_USER}'@'%' IDENTIFIED BY '${app_password}';
GRANT ALL PRIVILEGES ON \`${MARIADB_DATABASE}\`.* TO '${MARIADB_USER}'@'%';
FLUSH PRIVILEGES;
SQL

    mariadb-admin \
        --protocol=socket \
        --socket="$socket" \
        -uroot \
        -p"$MARIADB_ROOT_PASSWORD" \
        shutdown
    wait "$temp_pid"
    trap - EXIT HUP INT TERM
    echo "MariaDB initialization complete" >&2
fi

exec "$@"
