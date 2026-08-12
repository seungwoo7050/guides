#!/bin/sh
set -eu

# [Implementation 6] 환경·secret을 preflight하고 worker 전용 복사본의 권한을 좁힙니다.
: "${DB_HOST:?DB_HOST가 필요합니다.}"
: "${DB_NAME:?DB_NAME이 필요합니다.}"
: "${DB_USER:?DB_USER가 필요합니다.}"
: "${DB_PASSWORD_FILE:?DB_PASSWORD_FILE이 필요합니다.}"

if [ ! -r "$DB_PASSWORD_FILE" ]; then
    echo "DB_PASSWORD_FILE을 읽을 수 없습니다: $DB_PASSWORD_FILE" >&2
    exit 1
fi

# 호스트 비밀 파일의 권한은 유지하고 PHP-FPM 작업자에게 필요한 읽기 권한만 부여합니다.
runtime_secret_dir=/run/app-secrets
runtime_password_file="$runtime_secret_dir/db_password"
install -d -m 0750 -o root -g www-data "$runtime_secret_dir"
install -m 0440 -o root -g www-data "$DB_PASSWORD_FILE" "$runtime_password_file"
export DB_PASSWORD_FILE="$runtime_password_file"

# [Implementation 7] 완성된 bootstrap CLI가 성공한 경우에만 최종 FPM process를 exec합니다.
php /opt/app/bootstrap.php
exec "$@"
