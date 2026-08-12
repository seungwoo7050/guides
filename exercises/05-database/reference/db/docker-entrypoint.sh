#!/bin/sh
set -eu

# [Implementation 3] 환경값과 file secret의 배타성 및 identifier 경계를 먼저 검증합니다.
file_env() {
    var="$1"
    file_var="${var}_FILE"
    default_value="${2:-}"

    eval "value=\${$var:-}"
    eval "file_path=\${$file_var:-}"

    if [ -n "$value" ] && [ -n "$file_path" ]; then
        echo "$var와 $file_var는 함께 지정할 수 없습니다." >&2
        exit 1
    fi

    if [ -n "$file_path" ]; then
        if [ ! -r "$file_path" ]; then
            echo "$file_var 파일을 읽을 수 없습니다." >&2
            exit 1
        fi
        value="$(cat "$file_path")"
    elif [ -z "$value" ]; then
        value="$default_value"
    fi

    export "$var=$value"
    unset "$file_var"
}

require_identifier() {
    label="$1"
    value="$2"
    case "$value" in
        ''|*[!A-Za-z0-9_]*)
            echo "$label에는 영문자, 숫자와 밑줄만 사용할 수 있습니다." >&2
            exit 1
            ;;
    esac
}

sql_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e "s/'/''/g"
}

file_env MARIADB_ROOT_PASSWORD
file_env MARIADB_PASSWORD

: "${MARIADB_ROOT_PASSWORD:?MARIADB_ROOT_PASSWORD가 필요합니다.}"
: "${MARIADB_DATABASE:?MARIADB_DATABASE가 필요합니다.}"
: "${MARIADB_USER:?MARIADB_USER가 필요합니다.}"
: "${MARIADB_PASSWORD:?MARIADB_PASSWORD가 필요합니다.}"

require_identifier MARIADB_DATABASE "$MARIADB_DATABASE"
require_identifier MARIADB_USER "$MARIADB_USER"

# [Implementation 4] system datadir 존재 여부만 최초 초기화의 authoritative state로 사용합니다.
datadir=/var/lib/mysql
socket=/run/mysqld/mysqld.sock
install -d -m 0755 -o mysql -g mysql /run/mysqld "$datadir"

if [ ! -d "$datadir/mysql" ]; then
    echo "데이터 디렉터리를 초기화합니다." >&2
    mariadb-install-db \
        --user=mysql \
        --datadir="$datadir" \
        --skip-test-db \
        --auth-root-authentication-method=socket >/dev/null

    # [Implementation 5] 외부 TCP를 닫은 임시 server만 띄우고 readiness를 제한 시간 안에 판정합니다.
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
        counter=$(expr "$counter" + 1)
    done
    if [ "$ready" -ne 1 ]; then
        echo "임시 MariaDB가 제한 시간 안에 준비되지 않았습니다." >&2
        exit 1
    fi

    root_password=$(sql_escape "$MARIADB_ROOT_PASSWORD")
    app_password=$(sql_escape "$MARIADB_PASSWORD")

    # [Implementation 6] socket으로 계정·DB를 적용하고 임시 server를 정상 종료한 뒤 최종 PID 1을 공개합니다.
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
    echo "데이터베이스 초기화를 마쳤습니다." >&2
fi

exec "$@"
