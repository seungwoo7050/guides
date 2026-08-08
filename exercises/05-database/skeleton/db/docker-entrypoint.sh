#!/bin/sh
set -eu

# TODO:
# 1. MARIADB_ROOT_PASSWORD(_FILE)과 MARIADB_PASSWORD(_FILE)을 읽습니다.
# 2. 필수값과 안전한 데이터베이스·사용자 식별자를 검증합니다.
# 3. /run/mysqld와 /var/lib/mysql의 소유권을 준비합니다.
# 4. /var/lib/mysql/mysql이 없을 때만 다음 작업을 수행합니다.
#    - mariadb-install-db 실행
#    - 로컬 소켓만 사용하는 임시 서버 시작
#    - 제한 시간 안에서 준비 상태 대기
#    - 관리자, 데이터베이스, 애플리케이션 사용자와 권한 구성
#    - 임시 서버를 정상 종료하고 종료 완료 대기
# 5. mariadbd가 PID 1이 되도록 Docker CMD를 exec로 실행합니다.

echo "skeleton의 시작 스크립트는 아직 구현되지 않았습니다." >&2
exit 1
