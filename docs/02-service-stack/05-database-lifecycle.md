# 데이터베이스 컨테이너의 생명주기

데이터베이스는 컨테이너 안에서 실행되는 또 하나의 서버 프로세스지만 일반적인 무상태 서비스와 결정적인 차이가 있습니다. 프로세스를 교체해도 데이터는 남아야 합니다.

이 장에서는 MariaDB를 예로 다음 흐름을 다룹니다.

```text
빈 볼륨
→ 시스템 테이블 초기화
→ 임시 서버 기동
→ 사용자·DB·권한 설정
→ 임시 서버 정상 종료
→ 본 서버를 포그라운드에서 실행
→ 재시작과 재생성
→ 백업과 복원
```

목표는 SQL 문법을 폭넓게 배우는 것이 아니라 데이터베이스 서버의 상태 전이를 이해하는 것입니다.

## 1. 데이터베이스가 특별한 이유

웹 게이트웨이나 애플리케이션 코드는 대체로 이미지에서 다시 만들 수 있습니다. 반면 데이터베이스의 사용자 데이터는 실행 중 계속 변합니다.

데이터베이스 파일을 컨테이너의 쓰기 가능 계층에 두면 다음 문제가 생깁니다.

- 컨테이너 삭제 시 데이터도 삭제됩니다.
- 이미지 업데이트를 위해 컨테이너를 교체하기 어렵습니다.
- 백업할 위치와 데이터 수명이 불분명합니다.
- 운영자가 컨테이너와 데이터를 같은 단위로 오해할 수 있습니다.

따라서 서버 프로세스와 데이터 저장소의 수명을 분리합니다.

```text
MariaDB 컨테이너   필요에 따라 재생성 가능
        │
        ▼
이름 있는 볼륨      명시적으로 삭제하기 전까지 유지
```

## 2. 데이터 디렉터리

MariaDB의 기본 데이터 디렉터리는 일반적으로 `/var/lib/mysql`입니다. 여기에는 다음이 저장됩니다.

- MariaDB가 권한과 역할을 관리하는 시스템 데이터베이스
- 애플리케이션 데이터베이스의 테이블과 인덱스
- InnoDB 관련 데이터와 로그
- 서버 상태를 유지하는 파일

이 디렉터리는 단순한 SQL 덤프가 아니라 서버 버전과 스토리지 엔진이 해석하는 내부 파일 구조입니다.

Compose에서 이름 있는 볼륨을 마운트합니다.

```yaml
services:
  db:
    volumes:
      - db-data:/var/lib/mysql

volumes:
  db-data:
```

컨테이너가 바뀌어도 같은 볼륨을 다시 마운트하면 기존 데이터 디렉터리를 사용합니다.

## 3. 빈 디렉터리에서 바로 서버를 시작할 수 없는 이유

MariaDB는 사용자 데이터만 읽는 것이 아닙니다. 인증, 권한, 역할, 플러그인 등의 정보를 시스템 테이블에서 읽습니다. 완전히 빈 디렉터리에는 이 테이블이 없습니다.

```text
빈 /var/lib/mysql
      │
      │ mariadb-install-db
      ▼
mysql 시스템 DB와 시스템 테이블 생성
      │
      ▼
mariadbd를 정상적으로 시작할 수 있는 데이터 디렉터리
```

`mariadb-install-db`는 상시 실행 서버가 아니라 데이터 디렉터리를 초기화하고 종료하는 배포 도구입니다.

## 4. 최초 초기화

대표적인 명령:

```sh
mariadb-install-db \
  --user=mysql \
  --datadir=/var/lib/mysql \
  --skip-test-db
```

### `--user=mysql`

생성되는 파일을 MariaDB 서버가 사용할 `mysql` 사용자 소유로 만듭니다. 서버 실행 사용자와 파일 소유자가 맞지 않으면 권한 거부 오류가 발생할 수 있습니다.

### `--datadir`

시스템 테이블을 만들 위치입니다. 이후 `mariadbd`가 사용하는 데이터 디렉터리와 반드시 같아야 합니다.

### `--skip-test-db`

테스트 데이터베이스와 불필요한 초기 계정을 만들지 않습니다. 설치 도구와 버전에 따라 초기 인증 방식이 다를 수 있으므로 실제 생성 결과를 확인합니다.

## 5. 최초 실행 판별

컨테이너 시작 스크립트는 매번 실행됩니다. 초기화 명령은 매번 실행하면 안 됩니다.

일반적인 판별 방식은 다음과 같습니다.

```sh
if [ ! -d "$DATADIR/mysql" ]; then
    mariadb-install-db ...
    # 최초 설정
fi
```

`$DATADIR/mysql`은 시스템 데이터베이스 디렉터리입니다. 존재하면 시스템 테이블 초기화가 적어도 한 번 수행된 것으로 판단합니다.

이 가드가 필요한 이유:

- 재시작 때 기존 시스템 테이블을 다시 만들지 않습니다.
- 애플리케이션 DB와 사용자를 매번 초기 상태로 되돌리지 않습니다.
- 빈 볼륨과 기존 상태가 있는 볼륨을 구분합니다.

다만 디렉터리 존재 여부만으로 초기화가 완전히 성공했음을 보장할 수는 없습니다. 일부 파일만 만들어진 상태에서 초기화가 실패할 수 있습니다. 더 견고한 구현은 임시 디렉터리에서 초기화한 뒤 원자적으로 전환하거나 완료 마커와 실제 서버 검증을 함께 사용합니다. 이 가이드의 작은 실습에서는 시스템 데이터베이스의 존재 여부를 기준으로 판단하고 중간 실패 시 볼륨 상태를 직접 검사합니다.

## 6. 디렉터리와 권한 준비

시작 스크립트가 관리자 권한으로 시작하는 이유 중 하나는 디렉터리 소유권을 준비하기 위해서입니다.

```sh
install -d -m 0755 -o mysql -g mysql /run/mysqld /var/lib/mysql
```

- `/run/mysqld`: 소켓과 PID 파일 같은 실행 중 생성 파일
- `/var/lib/mysql`: 영속 데이터

이름 있는 볼륨의 최상위 디렉터리 소유권이 예상과 다를 수 있으므로 시작할 때 확인합니다.

```sh
stat -c '%U:%G %a %n' /var/lib/mysql /run/mysqld
```

전체 데이터 디렉터리에 매번 재귀 `chown`을 실행하면 큰 데이터셋에서는 시작 시간이 길어질 수 있습니다. 초기 상태와 실제로 필요한 경로만 변경하는 전략을 검토합니다.

## 7. 초기화용 임시 서버

시스템 테이블을 만든 뒤 SQL로 root 인증, 애플리케이션 DB와 사용자를 설정해야 합니다. SQL을 실행하려면 서버가 잠시 실행되어야 합니다.

```sh
mariadbd \
  --user=mysql \
  --datadir=/var/lib/mysql \
  --skip-networking \
  --socket=/run/mysqld/mysqld.sock &
pid=$!
```

### `--skip-networking`

초기 root 인증과 사용자 설정이 끝나기 전에 TCP 연결을 받지 않습니다. 같은 컨테이너의 Unix socket으로만 초기화 명령을 수행합니다.

### 백그라운드 실행과 `$!`

시작 스크립트가 SQL 설정 작업을 계속하기 위해 임시 서버를 백그라운드로 실행합니다. 가장 최근에 백그라운드로 실행한 프로세스의 PID를 `$!`로 저장합니다.

이는 최종 서버 실행 방식이 아닙니다. 초기화 작업 동안만 일시적으로 사용합니다.

## 8. 준비 상태 대기

프로세스를 시작한 직후 소켓과 시스템 테이블이 준비됐다고 가정하지 않습니다.

```sh
ready=0
for _ in $(seq 1 60); do
    if mariadb-admin \
        --protocol=socket \
        --socket=/run/mysqld/mysqld.sock \
        ping --silent
    then
        ready=1
        break
    fi
    sleep 1
done

if [ "$ready" -ne 1 ]; then
    echo "임시 MariaDB가 제한 시간 안에 준비되지 않았습니다." >&2
    kill -TERM "$pid" 2>/dev/null || true
    wait "$pid" || true
    exit 1
fi
```

재시도에는 반드시 종료 조건이 있어야 합니다. 무한 대기는 실패를 숨기고 자동화 전체를 멈춥니다.

`mariadb-admin ping`의 성공은 서버가 프로토콜 요청에 응답한다는 신호입니다. 애플리케이션 사용자의 권한이나 특정 쿼리 성공까지 보장하지는 않습니다.

## 9. 초기 SQL

초기화용 소켓으로 SQL을 실행합니다.

```sh
mariadb --protocol=socket --socket=/run/mysqld/mysqld.sock -uroot <<SQL
CREATE DATABASE IF NOT EXISTS `appdb`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'appuser'@'%'
  IDENTIFIED BY 'replace-me';

GRANT ALL PRIVILEGES ON `appdb`.* TO 'appuser'@'%';
FLUSH PRIVILEGES;
SQL
```

실제 entrypoint에서 변수 값을 SQL 문자열에 직접 삽입하면 SQL 인젝션이나 문법 오류가 생길 수 있습니다.

- DB 이름과 사용자 이름은 허용 문자 집합을 제한합니다.
- 문자열 비밀번호의 작은따옴표를 SQL 규칙에 맞게 이스케이프합니다.
- 비밀번호를 로그에 출력하지 않습니다.
- 가능하면 공식 이미지가 제공하는 검증된 초기화 기능이나 애플리케이션 마이그레이션 도구를 사용합니다.

### 최소 권한

애플리케이션 사용자는 필요한 데이터베이스에만 권한을 갖게 합니다. 운영 애플리케이션이 root 계정을 사용하지 않습니다.

실습에서는 스키마 생성과 CRUD를 위해 한 DB 전체 권한을 주지만 실제 시스템에서는 마이그레이션 계정과 런타임 계정을 분리할 수 있습니다.

## 10. 관리자 계정 인증

MariaDB 배포판은 초기 관리자 계정에 Unix 소켓 인증을 적용할 수 있습니다. 관리자 비밀번호 설정 방법은 버전과 패키지 정책에 따라 다릅니다.

실습 시작 스크립트는 로컬 소켓으로 초기 설정을 수행한 뒤 다음과 같은 형태로 비밀번호 인증을 설정합니다.

```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY '...';
```

다음 기동부터 상태 검사는 비밀값 파일의 관리자 비밀번호를 사용합니다.

보안상 root의 원격 접속용 계정은 만들지 않습니다. 애플리케이션 컨테이너는 별도 `appuser`로 TCP 연결합니다.

## 11. 임시 서버 정상 종료

초기 SQL이 끝나면 임시 서버를 정상 종료합니다.

```sh
mariadb-admin \
  --protocol=socket \
  --socket=/run/mysqld/mysqld.sock \
  -uroot \
  -p"$MARIADB_ROOT_PASSWORD" \
  shutdown

wait "$pid"
```

`shutdown`은 서버가 버퍼를 반영하고 스토리지 엔진을 정리할 기회를 줍니다. `kill -9`는 이 과정을 건너뜁니다.

`wait`는 백그라운드 프로세스가 완전히 끝날 때까지 기다립니다. 임시 서버가 아직 데이터 디렉터리를 사용 중인데 본 서버를 시작하면 파일 잠금이나 복구 충돌이 발생할 수 있습니다.

실패 또는 시그널을 받았을 때 임시 서버를 정리하도록 `trap`을 둘 수 있습니다.

## 12. 본 서버 실행

초기화 블록이 끝나면 entrypoint가 Dockerfile의 CMD를 실행합니다.

```sh
exec "$@"
```

Dockerfile:

```dockerfile
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["mariadbd", "--user=mysql", "--console"]
```

`exec` 뒤에는 셸이 남지 않습니다. `mariadbd`가 PID 1이 되어 Docker의 SIGTERM을 직접 받습니다.

`--console`은 로그를 컨테이너 stdout/stderr로 보내 관찰하기 쉽게 합니다.

## 13. MariaDB 설정 파일

Debian 계열에서 서버 설정은 보통 `/etc/mysql/mariadb.conf.d/*.cnf`에 둡니다. 정확한 include 순서는 이미지와 패키지를 확인합니다.

예제:

```ini
[mariadbd]
bind-address = 0.0.0.0
port = 3306
datadir = /var/lib/mysql
socket = /run/mysqld/mysqld.sock
pid-file = /run/mysqld/mysqld.pid
skip-name-resolve
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
innodb_buffer_pool_size = 128M
max_connections = 80
```

### `bind-address`

`0.0.0.0`은 컨테이너의 모든 IPv4 인터페이스에서 연결을 받습니다. 애플리케이션이 다른 컨테이너에 있으므로 루프백에서만 수신하면 접근할 수 없습니다.

이 설정만으로 호스트 외부에 공개되는 것은 아닙니다. Compose에 `ports`가 없으면 같은 Docker 네트워크에서만 접근합니다.

### `skip-name-resolve`

클라이언트 IP의 역방향 DNS 조회를 끕니다. 컨테이너 네트워크에서 불필요한 DNS 지연을 줄일 수 있습니다. 대신 MariaDB 권한의 `host` 부분에 DNS 이름을 사용하지 말고 IP 패턴 또는 `%` 같은 정책을 사용합니다.

### `utf8mb4`

MariaDB/MySQL의 역사적인 `utf8`은 3바이트 문자 집합을 의미할 수 있습니다. 이모지와 보조 평면 문자를 포함한 전체 유니코드 범위를 UTF-8로 저장하려면 `utf8mb4`를 사용합니다.

문자 집합은 서버, DB, 테이블, 컬럼, 연결 수준에서 다를 수 있습니다. 서버 기본값만 설정했다고 기존 테이블이 자동으로 변환되지는 않습니다.

### `innodb_buffer_pool_size`

InnoDB의 데이터와 인덱스 페이지를 메모리에 캐시하는 주요 영역입니다. 전용 DB 서버에서는 큰 비중을 할당할 수 있지만 같은 호스트에서 여러 컨테이너가 메모리를 공유한다면 전체 자원 제한을 고려해야 합니다.

값을 임의로 크게 잡으면 OOM이 발생할 수 있습니다. 실제 데이터셋, 캐시 적중률, 컨테이너 메모리 제한을 관찰해 조정합니다.

### `max_connections`

동시 연결 수의 상한입니다. 값을 크게 설정한다고 처리량이 자동으로 늘지는 않습니다. 각 연결의 메모리 사용량, 애플리케이션 연결 풀, 쿼리 시간에 따라 오히려 자원 고갈이 빨라질 수 있습니다.

```text
필요 연결 수 ≈ app 인스턴스 수 × 인스턴스당 풀 상한 + 관리 여유
```

## 14. DB 네트워크 노출

다음 두 설정을 구분합니다.

```ini
bind-address = 0.0.0.0
```

MariaDB가 컨테이너 내부 모든 인터페이스에서 연결을 받도록 합니다.

```yaml
ports:
  - "3306:3306"
```

호스트 포트로 공개합니다.

애플리케이션이 같은 Docker 네트워크에 있다면 두 번째 설정은 필요하지 않습니다.

```text
app → db:3306             가능
host → localhost:3306    ports가 없으면 불가
```

DB를 내부 네트워크에만 두면 무단 스캔과 직접 접근 표면을 줄일 수 있습니다. 네트워크 격리가 DB 인증을 대신하는 것은 아닙니다.

## 15. 데이터베이스 상태 검사

Compose 예제:

```yaml
healthcheck:
  test:
    - CMD-SHELL
    - >-
      mariadb-admin
      --protocol=socket
      --socket=/run/mysqld/mysqld.sock
      -uroot
      -p"$$(cat /run/secrets/db_root_password)"
      ping --silent
  interval: 5s
  timeout: 3s
  retries: 20
  start_period: 10s
```

`$$`는 Compose 보간을 피하고 컨테이너 셸에 `$` 하나를 전달합니다.

### 로컬 소켓 연결 확인

같은 컨테이너 안에서 서버 프로세스와 로컬 소켓의 준비 상태를 확인합니다. 외부 네트워크 경로까지 검사하지는 않습니다.

### TCP 연결 확인

애플리케이션 컨테이너에서 `db:3306`으로 검사하면 Docker DNS, 네트워크, TCP, 인증을 함께 확인할 수 있습니다.

### 인증하지 않은 연결 확인

MariaDB/MySQL의 일부 연결 확인 명령은 인증에 실패해도 서버가 응답한다는 사실만으로 생존 상태를 판단할 수 있습니다. 운영 상태 검사에서 무엇을 정상으로 정의하는지 명확히 해야 합니다. 특정 사용자의 실제 쿼리 가능성을 요구한다면 작은 읽기 쿼리를 별도로 사용합니다.

상태 검사에 쓰기 쿼리를 넣지 않습니다.

## 16. 재시작, 재생성, 볼륨 삭제

### 재시작

```sh
docker compose restart db
```

같은 컨테이너 파일 시스템과 볼륨을 유지하며 프로세스를 다시 시작합니다. 시작 스크립트는 다시 실행되고 최초 실행 판별 결과에 따라 초기화를 건너뜁니다.

### 재생성

```sh
docker compose up -d --force-recreate db
```

새 컨테이너를 만들지만 같은 이름 있는 볼륨을 마운트합니다. 데이터는 남습니다.

### down

```sh
docker compose down
```

컨테이너는 제거하지만 이름 있는 볼륨은 기본적으로 남습니다.

### 볼륨 삭제

```sh
docker compose down -v
```

데이터 디렉터리가 삭제됩니다. 다음 `up`은 빈 볼륨에서 최초 초기화를 다시 수행합니다.

이 네 시나리오를 실제로 실행해 결과를 구분해야 합니다.

## 17. 백업과 복원

컨테이너와 볼륨이 있다고 해서 백업이 된 것은 아닙니다. 호스트 디스크 손상, 운영자 실수, SQL 삭제, 볼륨 제거에 대비하려면 별도 사본이 필요합니다.

### 논리 백업

```sh
docker compose exec -T db \
  mariadb-dump -uappuser -p"..." appdb \
  > backups/appdb.sql
```

장점:

- 사람이 읽을 수 있는 SQL 형태입니다.
- 테이블 단위로 내용을 확인할 수 있습니다.
- 다른 서버로 옮기기 쉽습니다.

단점:

- 큰 DB에서는 시간이 오래 걸리고 CPU를 많이 사용할 수 있습니다.
- 일관된 스냅샷을 위한 옵션을 확인해야 합니다.
- 사용자와 서버 전역 설정은 별도 백업이 필요할 수 있습니다.

비밀번호를 명령행 인자로 전달하면 다른 프로세스 검사 도구 등에 노출될 수 있습니다. 실습에서는 단순화를 위해 제한적으로 사용하되 운영 환경에서는 옵션 파일, 비밀값 파일, 전용 백업 도구 등을 검토합니다.

### 복원

```sh
docker compose exec -T db \
  mariadb -uappuser -p"..." appdb \
  < backups/appdb.sql
```

백업 성공 메시지만 확인하지 않습니다. 빈 DB 또는 별도 테스트 환경에 실제로 복원하고 데이터 개수와 제약 조건을 검증합니다.

> 복원해 보지 않은 백업은 복구 수단으로 검증된 것이 아닙니다.

### 물리 백업

데이터 파일을 스토리지 엔진이 정의한 일관된 상태로 복사합니다. 서버 버전과 엔진에 더 강하게 결합되며 실행 중 단순 `cp`는 일관성을 깨뜨릴 수 있습니다. MariaDB Backup 같은 전용 도구를 사용합니다. 이 가이드의 실습은 논리 백업에 한정합니다.

## 18. 인덱스의 운영적 의미

인덱스 설계는 주로 데이터 모델과 쿼리를 다루는 백엔드·DB 개발 영역입니다. 그러나 인덱스 부재는 CPU, 디스크 I/O, 응답 시간, 연결 점유를 통해 인프라 장애처럼 나타날 수 있습니다. 운영자가 최소한 진단할 수 있어야 합니다.

### 18.1 전체 테이블 스캔

다음 쿼리를 생각합니다.

```sql
SELECT * FROM users WHERE email = 'a@users.local.test';
```

`email`에 사용할 수 있는 인덱스가 없으면 DB는 조건을 확인하기 위해 많은 행을 읽을 수 있습니다. 테이블이 커질수록 읽기량과 실행 시간이 증가합니다.

### 18.2 기본키와 일반 인덱스

```sql
CREATE TABLE users (
  id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  name VARCHAR(255) NOT NULL,
  INDEX idx_users_email (email)
);
```

- 기본키: 각 행을 고유하게 식별합니다.
- 고유 인덱스: 값의 중복을 막으면서 조회 구조도 제공합니다.
- 일반 인덱스: 중복을 허용하면서 검색을 가속합니다.

이메일이 도메인 규칙상 유일해야 한다면 일반 인덱스보다 UNIQUE 제약 조건이 데이터 무결성과 조회 요구를 함께 표현합니다.

### 18.3 복합 인덱스

```sql
INDEX idx_orders_user_created (user_id, created_at)
```

일반적으로 인덱스의 선두 컬럼부터 이어지는 조건에 유리합니다.

- `WHERE user_id = ?`에 활용될 가능성이 높습니다.
- `WHERE user_id = ? AND created_at >= ?`에 활용될 가능성이 높습니다.
- `WHERE created_at >= ?`만 있는 경우 같은 인덱스를 충분히 활용하지 못할 수 있습니다.

실제 판단은 쿼리와 실행 계획을 확인해야 합니다.

### 18.4 `EXPLAIN`

```sql
EXPLAIN SELECT * FROM users WHERE email = 'a@users.local.test';
```

표현은 MariaDB 버전에 따라 다를 수 있지만 입문 단계에서는 다음을 확인합니다.

- 어떤 테이블을 읽는가?
- 후보 키와 실제 선택 키는 무엇인가?
- 예상 행 수는 얼마나 되는가?
- 전체 스캔에 가까운 접근 방식인가?
- 추가 정렬이나 임시 작업이 있는가?

`EXPLAIN`에서 인덱스를 선택했다고 무조건 빠른 것은 아닙니다. 반환 행이 테이블 대부분이라면 스캔이 합리적일 수 있고 아주 작은 테이블에서는 인덱스 사용의 이점이 작을 수 있습니다.

### 18.5 인덱스 비용

인덱스는 무료가 아닙니다.

- 디스크 공간 증가
- 버퍼 풀 사용 증가
- INSERT 시 인덱스 갱신
- UPDATE한 컬럼의 인덱스 갱신
- DELETE 시 인덱스 갱신
- 백업과 스키마 변경 시간 증가

조회가 느리다고 모든 컬럼에 인덱스를 추가하지 않습니다. 실제 느린 쿼리, 필터·조인·정렬 패턴, 쓰기 부하를 기준으로 선택합니다.

### 18.6 서버 증설과 쿼리 개선

CPU나 메모리를 늘리기 전에 다음을 확인합니다.

1. 느린 쿼리가 어떤 테이블과 행을 읽는가?
2. 불필요한 전체 스캔이 있는가?
3. 필요한 행보다 많은 컬럼과 행을 반환하는가?
4. 연결 풀이 느린 쿼리를 기다리며 고갈되는가?
5. 버퍼 풀이 데이터셋에 비해 지나치게 작은가?

인덱스 하나로 읽기량이 수백만 행에서 수십 행으로 줄 수 있다면 서버 증설보다 먼저 해결해야 할 가능성이 큽니다. 반대로 쿼리가 이미 적절하고 working set이 메모리보다 크다면 자원 조정이 필요할 수 있습니다.

이 가이드에서는 고급 옵티마이저, online DDL, 파티셔닝, 샤딩은 다루지 않습니다.

## 19. 실습

실습 위치:

```sh
python3 scripts/new-workspace.py exercises/05-database
cd exercises/05-database
```

### 실습 1: 최초 초기화

```sh
./verify.sh workspace
```

검증 스크립트는 비밀값 파일을 준비하고 커스텀 MariaDB 이미지를 빌드합니다. 첫 시작 로그에서 시스템 테이블 초기화와 초기 SQL 실행을 확인합니다.

### 실습 2: 재시작과 재생성

검증 중 테이블에 marker 행을 넣고 컨테이너를 재생성합니다. marker가 남아 있어야 합니다. 로그에서 초기화 블록이 다시 실행되지 않았는지 확인합니다.

### 실습 3: 백업과 복원

자신이 완성한 `workspace/backup.sh`와 `workspace/restore.sh`를 실행하고 다음을 확인합니다.

- 덤프가 호스트의 어느 경로에 생기는가?
- 복원 전에 어떤 DB 상태를 준비하는가?
- 복원 후 어떤 SQL로 결과를 검증하는가?

### 실습 4: 인덱스 전후 `EXPLAIN`

`workspace/sql/index-demo.sql`은 일정한 수의 행을 만들고 email 조회의 실행 계획을 비교합니다.

다음 숫자 하나만 비교하지 않습니다.

```text
실행 시간 숫자 하나
```

개발 노트북의 작은 데이터에서는 캐시와 측정 오차의 영향이 큽니다. 실제 선택 키와 예상 행 수의 변화를 함께 확인합니다.

수명 관찰과 자신의 설명을 정리한 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## 20. 데이터 수명과 관련된 오해

### “컨테이너를 재시작하면 데이터베이스가 초기화됩니다”

시작 스크립트는 다시 실행되지만 볼륨의 시스템 데이터베이스가 남아 있으므로 최초 실행 블록을 건너뛰어야 합니다.

### “bind-address 0.0.0.0이면 인터넷에 공개됩니다”

서버가 컨테이너의 모든 IPv4 인터페이스에서 연결을 받는다는 뜻입니다. 호스트 외부 공개 여부는 Compose `ports`와 호스트 방화벽 등 다른 네트워크 설정이 결정합니다.

### “볼륨이면 백업이 필요 없습니다”

볼륨은 컨테이너 삭제와 데이터 수명을 분리할 뿐 별도 장애 영역의 사본이 아닙니다.

### “비밀값 파일만 바꾸면 기존 데이터베이스 비밀번호도 바뀝니다”

이 장의 비밀번호 설정 SQL은 최초 실행 블록에서 한 번만 실행됩니다. 이미 초기화된 볼륨을 유지한 채 비밀값 파일만 바꾸면 데이터베이스 계정의 실제 비밀번호는 이전 값으로 남고 상태 검사와 애플리케이션 인증이 실패합니다. 비밀번호 회전은 인증된 `ALTER USER`, 관련 비밀값 교체, 의존 서비스 재시작을 하나의 절차로 수행해야 합니다.

### “max_connections를 크게 하면 연결 오류가 해결됩니다”

느린 쿼리와 과도한 연결 풀이 원인이라면 메모리 고갈을 늦출 뿐이거나 오히려 악화할 수 있습니다.

### “인덱스는 많을수록 좋습니다”

쓰기 비용, 저장 공간, 캐시 비용이 있습니다. 실제 쿼리를 기준으로 설계합니다.

## 21. 데이터 운영 원칙

- 데이터베이스 데이터 디렉터리는 컨테이너 수명과 분리해 볼륨에 둡니다.
- 빈 데이터 디렉터리에는 시스템 테이블 초기화가 필요합니다.
- 최초 실행 판별이 초기화와 일반 재시작을 구분합니다.
- 초기 설정 중 임시 서버는 네트워크를 끄고 소켓으로만 사용합니다.
- 임시 서버는 정상 종료하고 `wait`한 뒤 본 서버를 시작합니다.
- 본 서버는 포그라운드의 PID 1로 실행합니다.
- 데이터베이스는 내부 네트워크에서만 접근하고 애플리케이션 전용 계정을 사용합니다.
- 상태 검사는 실제 데이터베이스 프로토콜 응답을 확인합니다.
- 볼륨 보존과 백업은 서로 다른 문제입니다.
- 인덱스는 인프라 자원 사용에 영향을 주지만 구체적인 설계는 쿼리·스키마 영역입니다.

## 공식 문서

- MariaDB `mariadb-install-db`: https://mariadb.com/docs/server/clients-and-utilities/deployment-tools/mariadb-install-db
- MariaDB 공식 컨테이너 이미지: https://hub.docker.com/_/mariadb
- MariaDB `EXPLAIN`: https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/analyze-and-explain-statements/explain
- MariaDB 인덱스: https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/optimization-and-indexes
- Docker 볼륨: https://docs.docker.com/engine/storage/volumes/
