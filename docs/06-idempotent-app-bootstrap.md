# 멱등한 애플리케이션 초기화

컨테이너 이미지를 실행하는 것만으로 애플리케이션이 항상 준비되는 것은 아닙니다. 데이터베이스 연결을 기다리고, schema를 만들고, 초기 데이터를 넣고, 쓰기 디렉터리 권한을 맞추는 시작 작업이 필요할 수 있습니다.

이 장의 핵심은 **멱등성(idempotency)** 입니다.

> 같은 초기화 절차를 여러 번 실행해도 시스템의 최종 상태가 의도치 않게 달라지지 않아야 합니다.

실습에서는 작은 메모 서비스를 사용합니다. 외부 제품이나 설치 도구에 기대지 않고 상태를 확인한 뒤 필요한 변경만 적용하는 흐름을 코드에서 직접 살펴봅니다.

## 1. 애플리케이션을 구성하는 상태

웹 애플리케이션의 상태를 최소 세 종류로 나눌 수 있습니다.

### 1.1 코드

- PHP, Python, JavaScript 등의 소스
- 정적 파일
- 실행 바이너리
- dependency

일반적으로 이미지에 포함하고 이미지 버전으로 배포합니다.

### 1.2 설정

- 데이터베이스 호스트와 데이터베이스 이름
- 공개 URL
- 로그 레벨
- 기능 flag
- 외부 서비스 주소

환경변수, 설정 파일, config service 등을 통해 환경별로 주입합니다.

### 1.3 런타임 데이터

- 데이터베이스 스키마와 행
- 사용자가 업로드한 파일
- 세션과 cache
- 애플리케이션이 생성한 상태 파일

볼륨 또는 외부 상태 저장소에 둡니다.

이 세 범주를 섞으면 배포와 복구가 어려워집니다. 예를 들어 이미지 안에 실행 시점 데이터베이스 덤프를 넣거나, 컨테이너 시작 스크립트가 매번 최신 소스를 다운로드하면 어떤 코드가 실행되는지 추적하기 어렵습니다.

## 2. 빌드 시점과 시작 시점

### 빌드 시점에 할 일

결과가 이미지에 고정되어도 되는 작업입니다.

- dependency 설치
- 소스 복사
- 정적 asset 빌드
- 기본 설정 복사
- 실행 사용자 생성
- 파일 권한 기본값 설정

### 시작 시점에 할 일

실행 환경이나 현재 볼륨과 데이터베이스 상태를 봐야 하는 작업입니다.

- 비밀값 파일 읽기
- 필수 설정 검증
- 의존 서비스 준비 대기
- 데이터베이스 스키마 변경
- 최초 데이터 입력
- 런타임 디렉터리 생성
- 최종 메인 프로세스 실행

시작 스크립트가 빌드 단계에서 할 수 있는 일까지 매번 반복하면 시작 시간이 늘고 외부 네트워크에 의존합니다. 반대로 환경마다 달라지는 비밀번호를 이미지 빌드 때 넣으면 이미지에 비밀이 남습니다.

## 3. 두 가지 코드 배포 전략

### 전략 A: 코드를 이미지에 포함

```dockerfile
COPY public/ /app/public/
COPY bin/ /app/bin/
```

장점:

- 이미지 digest와 실행 코드가 대응합니다.
- 동일 이미지를 다시 실행할 수 있습니다.
- rollback이 단순합니다.
- 시작할 때 외부 다운로드가 필요 없습니다.

일반적인 배포에서는 이 전략을 우선합니다.

### 전략 B: 시작 시 코드를 다운로드

시작 스크립트가 빈 볼륨에 애플리케이션 코드를 내려받습니다.

장점:

- 하나의 이미지로 여러 코드 버전을 선택할 수 있습니다.
- 기존 공유 호스팅 또는 가변 CMS 구조를 재현하기 쉽습니다.

단점:

- 시작이 외부 네트워크에 의존합니다.
- URL이 최신 파일을 가리키면 재현성이 약합니다.
- 부분 다운로드와 권한 복구 로직이 필요합니다.
- 코드와 사용자 업로드가 한 볼륨에 섞일 수 있습니다.

제품 특성상 필요할 수 있지만 편의만으로 일반 원칙처럼 사용하지 않습니다. 이 저장소의 애플리케이션 코드는 이미지에 포함합니다.

## 4. 부트스트랩 상태 머신

좋은 시작 스크립트는 단순한 명령 목록이 아니라 현재 상태를 원하는 상태로 수렴시키는 상태 머신으로 볼 수 있습니다.

```text
설정 읽기
   │
   ▼
필수값 유효? ── 아니오 ──▶ 명확한 오류로 종료
   │ 예
   ▼
데이터베이스 준비? ─ 아니오 ─▶ 제한된 재시도
   │ 예
   ▼
스키마 준비
   │
   ▼
고유 seed marker 원자적 삽입
   ├─ 새 marker ─▶ 같은 transaction에서 초기 데이터 삽입
   └─ 기존 marker ─▶ 초기 데이터 건너뜀
   │
   ▼
메인 프로세스로 exec
```

각 단계는 다음 조건을 만족해야 합니다.

- 성공과 실패가 종료 코드로 구분됩니다.
- 실패 메시지가 비밀값을 포함하지 않습니다.
- 여러 번 실행해도 중복 데이터나 파괴적 변경이 생기지 않습니다.
- 부분 성공 뒤 재실행할 수 있습니다.
- 무한 대기하지 않습니다.

## 5. 멱등성

수학적 의미의 완전한 멱등성과 운영 스크립트의 실용적 멱등성은 구분할 수 있습니다. 이 장에서는 다음을 목표로 합니다.

```text
초기 상태 S
초기화(S) = 원하는 상태 D
초기화(D) = D
```

예를 들어 다음 명령은 반복해도 테이블을 중복 생성하지 않습니다.

```sql
CREATE TABLE IF NOT EXISTS notes (...);
```

초기 데이터에는 고유 키와 `upsert`를 사용합니다.

```sql
INSERT INTO app_meta (`key`, `value`)
VALUES ('schema_version', '1')
ON DUPLICATE KEY UPDATE `value` = VALUES(`value`);
```

반면 다음은 매 실행마다 중복 행을 만듭니다.

```sql
INSERT INTO notes (body) VALUES ('first note');
```

동시 시작까지 안전하려면 고유한 초기 데이터 키를 두고, 조회와 삽입을 나누지 말고 데이터베이스의 원자적 삽입 결과로 적용 주체를 결정합니다.

## 6. 상태 조회와 원자적 전이를 구분합니다

상태 조회는 진단과 읽기 전용 판단에는 유용하지만, 조회 뒤 변경하는 check-then-act는 동시 실행에서 경쟁할 수 있습니다.

```text
인스턴스 A: marker 없음 확인 ─┐
                              ├─ 둘 다 seed 삽입 시도
인스턴스 B: marker 없음 확인 ─┘
```

파일처럼 단일 작성자만 있다는 조건이 분명하면 존재 확인 뒤 생성하는 흐름을 사용할 수 있습니다. 여러 인스턴스가 공유하는 데이터베이스에서는 unique constraint와 원자적 쓰기를 조정 장치로 사용합니다.

```sql
INSERT IGNORE INTO app_meta (meta_key, meta_value)
VALUES ('seed_v1', 'done');
```

스키마 변경 도구는 보통 적용된 버전 테이블과 migration lock을 관리합니다. SQL 파일을 무조건 매번 실행하거나 애플리케이션별 `SELECT` 결과로 적용 주체를 정하는 것보다 버전, 잠금과 트랜잭션을 추적할 수 있습니다.

상태 판정은 변경하려는 것과 같은 수준을 봐야 합니다.

- 데이터베이스 설치 상태를 파일 존재만으로 판단하지 않습니다.
- 사용자 존재를 단순히 전체 row 수로 판단하지 않습니다.
- 애플리케이션의 준비 상태를 TCP 포트 하나만으로 판단하지 않습니다.

## 7. POSIX `/bin/sh`

컨테이너 시작 스크립트는 작고 이식 가능한 셸 스크립트로 작성하는 경우가 많습니다. Debian의 `/bin/sh`는 보통 Bash가 아닌 `dash`이며, Alpine은 BusyBox `ash`를 사용합니다.

셰뱅이 `/bin/sh`라면 Bash 전용 기능을 사용하지 않습니다.

사용하지 않을 예:

```sh
[[ "$value" == "x" ]]
array=(a b)
local value=1
```

POSIX 형태:

```sh
[ "$value" = "x" ]
set -- a b
function_name() {
    value=1
}
```

함수 안 변수는 POSIX에서 자동 지역 변수가 아닙니다. 이름 충돌을 피하거나 서브셸을 사용합니다.

## 8. 엄격한 시작

```sh
#!/bin/sh
set -eu
```

### `set -e`

처리하지 않은 명령 실패에서 스크립트를 종료합니다. 초기화 일부가 실패했는데 다음 단계가 계속 실행되는 것을 줄입니다.

다만 조건문에 사용한 명령 실패는 종료되지 않습니다.

```sh
if database_is_ready; then
    ...
fi
```

`set -e`의 예외는 셸마다 미묘하므로 중요한 오류는 명시적으로 검사합니다.

### `set -u`

설정되지 않은 변수를 참조하면 실패합니다. 오타가 빈 문자열로 조용히 진행되는 것을 막습니다.

선택값은 기본값 확장을 사용합니다.

```sh
LOG_LEVEL="${LOG_LEVEL:-info}"
```

POSIX sh에는 표준 `pipefail`이 없습니다. `/bin/sh` 스크립트에 무조건 `set -o pipefail`을 넣지 않습니다.

## 9. 변수 인용

변수는 특별한 이유가 없으면 큰따옴표로 감쌉니다.

```sh
cat "$file_path"
exec "$@"
```

인용하지 않으면 변수 확장 뒤 공백 기준 word splitting과 glob 확장이 일어납니다.

```sh
file='my data.txt'
cat $file       # 두 인자로 분리될 수 있음
cat "$file"     # 한 경로
```

`"$@"`는 시작 스크립트에 전달된 인자 경계를 보존합니다. `"$*"`와 다릅니다.

## 10. 파라미터 확장

### 필수값

```sh
: "${DB_HOST:?DB_HOST가 필요합니다.}"
```

`:`는 아무 작업 없이 성공하는 명령입니다. 파라미터 확장의 검증 부작용만 사용합니다.

### 기본값을 사용하되 변수는 바꾸지 않음

```sh
port="${APP_PORT:-9000}"
```

### 기본값을 변수에 대입

```sh
: "${APP_ENV:=development}"
```

### 문자열 길이

```sh
if [ "${#password}" -lt 12 ]; then
    echo "비밀번호가 너무 짧습니다." >&2
    exit 1
fi
```

오류 메시지에 실제 비밀번호를 출력하지 않습니다.

## 11. 파일 기반 비밀값 읽기

애플리케이션이 `DB_PASSWORD` 또는 `DB_PASSWORD_FILE` 중 하나를 지원하도록 만들 수 있습니다.

```sh
file_env() {
    var="$1"
    file_var="${var}_FILE"
    default_value="${2:-}"

    eval "value=\${$var:-}"
    eval "file_path=\${$file_var:-}"

    if [ -n "$value" ] && [ -n "$file_path" ]; then
        echo "$var and $file_var are mutually exclusive" >&2
        exit 1
    fi

    if [ -n "$file_path" ]; then
        [ -r "$file_path" ] || {
            echo "$file_var is not readable" >&2
            exit 1
        }
        value="$(cat "$file_path")"
    elif [ -z "$value" ]; then
        value="$default_value"
    fi

    export "$var=$value"
    unset "$file_var"
}
```

POSIX sh에는 Bash의 간접 확장 `${!name}`이 없어서 통제된 변수 이름에 `eval`을 사용할 수 있습니다. 사용자 입력을 그대로 eval하지 않습니다.

호출:

```sh
file_env DB_PASSWORD
: "${DB_PASSWORD:?DB_PASSWORD가 필요합니다.}"
```

비밀값 파일 끝의 줄바꿈 처리도 생각해야 합니다. 셸의 명령 치환은 마지막 줄바꿈을 제거합니다. 비밀번호 생성 규칙과 소비자가 기대하는 바이트를 일치시킵니다.

Compose가 로컬 파일을 비밀값으로 마운트하면 호스트의 소유권과 권한이 그대로 적용될 수 있습니다. 시작 스크립트는 관리자 권한으로 파일을 읽더라도 PHP-FPM 작업자는 읽지 못하는 상황이 생깁니다. 호스트 파일의 `0600` 권한을 낮추는 대신, 시작할 때 `/run`의 `tmpfs`에 `root:www-data`, `0440` 복사본을 만들고 작업자에는 그 경로만 전달합니다. 복사본은 컨테이너가 사라질 때 함께 없어지며 작업자가 덮어쓸 수 없습니다.

## 12. 입력 검증

환경변수는 모두 문자열이며 신뢰할 수 없는 입력일 수 있습니다.

### 식별자 제한

데이터베이스 이름처럼 SQL 식별자로 사용할 값은 안전한 문자만 허용합니다.

```sh
require_identifier() {
    label="$1"
    value="$2"

    case "$value" in
        ''|*[!A-Za-z0-9_]*)
            echo "$label must contain only letters, digits, and underscore" >&2
            exit 1
            ;;
    esac
}
```

### 숫자 검증

```sh
case "$APP_PORT" in
    ''|*[!0-9]*)
        echo "APP_PORT는 숫자여야 합니다." >&2
        exit 1
        ;;
esac
```

숫자 모양뿐 아니라 허용 범위도 검사할 수 있습니다.

### URL과 호스트

문자열이 비어 있지 않다는 것만으로 유효한 URL은 아닙니다. 실제 parser 또는 연결 시점 오류를 명확하게 처리합니다.

검증은 공격 방지뿐 아니라 설정 오타를 시작 초기에 발견하는 운영 도구입니다.

## 13. 의존 서비스 준비 대기

Compose의 `service_healthy`가 있어도 애플리케이션은 실행 중 재연결과 독립 실행을 위해 자체적으로 횟수가 제한된 재시도를 수행할 수 있습니다.

PHP 예제:

```php
<?php
$attempts = 30;
for ($i = 1; $i <= $attempts; $i++) {
    try {
        $pdo = new PDO($dsn, $user, $password, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        ]);
        break;
    } catch (PDOException $e) {
        if ($i === $attempts) {
            fwrite(STDERR, "데이터베이스가 제한 시간 안에 준비되지 않았습니다.\n");
            exit(1);
        }
        sleep(2);
    }
}
```

로그에 예외 전체를 출력하면 DSN이나 사용자 정보가 노출될 수 있습니다. 개발 환경에서는 상세 원인을 보되 운영 환경에서는 민감 정보와 불필요한 출력을 제어합니다.

재시도 대상은 일시적 오류여야 합니다. 잘못된 비밀번호를 10분 동안 반복해도 해결되지 않습니다. 실습은 단순화를 위해 연결 오류를 같은 방식으로 재시도하지만, 운영 코드는 인증 실패와 연결 거부를 구분할 수 있습니다.

## 14. 스키마 변경

실습의 `bootstrap.php`는 다음 스키마를 만듭니다.

```sql
CREATE TABLE IF NOT EXISTS notes (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  body VARCHAR(500) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

그리고 버전을 기록합니다.

```sql
CREATE TABLE IF NOT EXISTS app_meta (
  meta_key VARCHAR(100) PRIMARY KEY,
  meta_value VARCHAR(255) NOT NULL
);
```

```sql
INSERT INTO app_meta (meta_key, meta_value)
VALUES ('schema_version', '1')
ON DUPLICATE KEY UPDATE meta_value = VALUES(meta_value);
```

실제 스키마 변경 작업에는 다음이 더 필요합니다.

- 버전별 변경 파일
- 적용 순서
- transaction 가능 여부
- rollback 또는 forward fix 정책
- schema lock과 서비스 중단 영향
- 여러 애플리케이션 인스턴스가 동시에 스키마를 변경하지 않도록 잠금

이 가이드는 단일 애플리케이션 인스턴스의 기초 흐름에 한정합니다.

## 15. 초기 데이터 입력의 멱등성

초기 note를 한 번만 넣으려면 `app_meta.meta_key`의 primary key가 동시 실행을 중재하게 합니다. 먼저 조회하지 않고 marker 삽입을 시도하며, 실제로 marker를 만든 transaction만 seed를 추가합니다.

```php
$pdo->beginTransaction();
try {
    $marker = $pdo->prepare(
        "INSERT IGNORE INTO app_meta (meta_key, meta_value)
         VALUES ('seed_v1', 'done')"
    );
    $marker->execute();

    if ($marker->rowCount() === 1) {
        $seed = $pdo->prepare('INSERT INTO notes (body) VALUES (:body)');
        $seed->execute(['body' => 'seed note']);
    }

    $pdo->commit();
} catch (Throwable $error) {
    try {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
    } catch (Throwable $rollbackError) {
        error_log('초기화 rollback에도 실패했습니다.');
    }
    throw $error;
}
```

marker와 seed가 같은 transaction에 있으므로 seed가 실패하면 marker도 rollback됩니다. 두 인스턴스가 동시에 시작해도 primary key가 삽입을 직렬화하고, marker 삽입 결과가 0행인 쪽은 seed를 건너뜁니다. MariaDB DDL은 implicit commit될 수 있으므로 table 준비와 이 데이터 transaction을 구분합니다.

## 16. 파일 권한과 쓰기 경로

이미지의 코드 파일은 관리자가 복사하더라도 작업자가 읽을 수 있는 0644 권한이면 실행할 수 있습니다. 애플리케이션이 쓰는 경로는 작업자 사용자 소유 또는 그룹 쓰기 권한이 필요합니다.

```dockerfile
RUN install -d -o www-data -g www-data -m 0750 /app/var
```

시작 스크립트에서 매번 전체 코드에 `chown -R`을 수행하지 않습니다. 큰 볼륨에서 느리고, 불변 코드까지 쓰기 가능하게 만들 수 있습니다.

경로를 역할별로 나눕니다.

```text
/app/public    읽기 전용 코드·정적 파일
/app/bin       읽기 전용 관리 스크립트
/app/var       애플리케이션 작업자가 쓰는 실행 중 데이터
/run/php       socket/PID 등 런타임 파일
```

## 17. 관리자 초기화와 비특권 실행

### Dockerfile `USER`

관리자 작업이 시작할 때 필요하지 않다면 이미지에서 처음부터 비특권 사용자로 실행합니다.

### 데몬 자체의 사용자 설정

PHP-FPM은 master가 worker를 `www-data`로 실행하도록 pool 설정을 제공합니다. MariaDB는 `--user=mysql`을 제공합니다.

### `gosu` 또는 `setpriv`

임의의 명령에 사용자 전환 기능이 없고 시작 스크립트가 관리자 권한으로 디렉터리를 준비해야 한다면 다음처럼 사용합니다.

```sh
exec gosu appuser "$@"
```

또는 util-linux의 `setpriv`를 사용할 수 있습니다.

도구를 넣는 것이 목적이 아닙니다. 최종 서비스 프로세스가 불필요한 관리자 권한을 갖지 않고 PID 1로 실행되게 하는 것이 목적입니다.

## 18. 마지막 `exec "$@"`

시작 스크립트 마지막:

```sh
exec "$@"
```

Dockerfile:

```dockerfile
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["php-fpm", "-F"]
```

실제 흐름:

```text
시작 셸 (PID 1)
  ├─ 비밀값 읽기
  ├─ 데이터베이스 대기
  ├─ bootstrap.php 실행
  └─ exec php-fpm -F

php-fpm master가 같은 PID 1 자리를 차지
```

`exec`를 빼면 셸이 PID 1로 남고 FPM은 자식이 됩니다. 시그널 전달과 종료 코드가 복잡해집니다.

## 19. 상태 검사와 초기화의 경계

초기화는 상태를 변경할 수 있습니다. 상태 검사는 반복 실행되므로 상태를 변경하면 안 됩니다.

### 초기화

- 스키마 변경
- 초기 데이터 입력
- 디렉터리 생성
- 설정 생성

### 상태 검사

- FPM ping
- 작은 읽기 요청
- 데이터베이스 연결 가능 여부

상태 검사에서 스키마를 변경하거나 초기 데이터를 복구하지 않습니다. 장애를 자동으로 숨기고 반복 쓰기 부하를 만들 수 있습니다.

## 20. 시작 스크립트의 전체 흐름

실습 완성 코드는 다음 순서를 사용합니다.

```sh
#!/bin/sh
set -eu

file_env DB_PASSWORD

: "${DB_HOST:?DB_HOST가 필요합니다.}"
: "${DB_NAME:?DB_NAME이 필요합니다.}"
: "${DB_USER:?DB_USER가 필요합니다.}"
: "${DB_PASSWORD:?DB_PASSWORD가 필요합니다.}"

php /app/bin/bootstrap.php

exec "$@"
```

실제 검증과 재시도는 `bootstrap.php`가 담당합니다. 셸은 비밀값 해석과 프로세스 인계에 집중합니다.

책임을 나누는 이유:

- SQL과 PDO 오류는 PHP에서 더 안전하게 처리합니다.
- shell quoting으로 SQL을 조립하지 않습니다.
- 시작 스크립트는 짧고 읽기 쉽습니다.
- 초기화 코드를 단독으로 검사할 수 있습니다.

모든 초기화를 셸 heredoc으로 작성해야 하는 것은 아닙니다. 작업에 적합한 언어를 사용합니다.

## 21. 부분 실패

다음 상황을 가정합니다.

1. notes 테이블 생성 성공
2. 초기 데이터 삽입 실패
3. 컨테이너 종료
4. 재시작

`CREATE TABLE IF NOT EXISTS`와 트랜잭션으로 묶은 초기 데이터 입력을 사용하면 재시작할 때 테이블 생성은 안전하게 넘어가고 데이터 입력을 다시 시도합니다.

반대로 초기화 완료 marker를 너무 일찍 만들면 재시작이 잘못된 상태를 정상으로 오판합니다.

부분 실패를 설계할 때 질문:

- 어떤 변경이 transaction 안에 있는가?
- 완료 판단은 어느 단계 뒤에 기록하는가?
- 재실행할 수 없는 외부 부작용이 있는가?
- 동시에 두 인스턴스가 실행하면 충돌하는가?

실습의 고유 marker는 동시에 시작한 애플리케이션의 seed 경쟁도 처리합니다. 다만 schema migration은 별도 잠금과 배포 순서를 고려해야 합니다.

## 22. 실습

실습 위치:

```sh
cd exercises/06-app-bootstrap
```

### 실습 1: 전체 완성 코드 실행

```sh
./verify.sh reference
```

검증 항목:

- 데이터베이스가 준비된 뒤 애플리케이션이 초기화됩니다.
- 스키마와 초기 데이터가 생성됩니다.
- HTTPS 요청이 note 목록을 반환합니다.
- 애플리케이션 컨테이너를 재시작해도 초기 데이터가 중복되지 않습니다.
- 새 note를 추가한 뒤 재생성해도 남습니다.
- 애플리케이션의 FPM 연결 확인과 게이트웨이 상태 검사가 정상입니다.

### 실습 2: 시작 코드의 초기화 완성

`skeleton/app/docker-entrypoint.sh`와 `skeleton/app/bin/bootstrap.php`의 TODO를 채웁니다.

- 필수 환경변수와 `DB_PASSWORD_FILE` 경로 검증
- 횟수를 제한한 데이터베이스 연결 재시도
- `IF NOT EXISTS` 기반 schema 준비
- 고유 marker를 원자적으로 삽입하고 같은 트랜잭션에서 초기 데이터 처리
- 초기화 성공 뒤 `exec "$@"`

### 실습 3: 필수 비밀값 누락

원본 secret 파일은 건드리지 않고 테스트용 Compose override에서 `DB_PASSWORD_FILE`을 존재하지 않는 경로로 바꾼 뒤 실행합니다.

예상:

- 애플리케이션 또는 데이터베이스가 명확한 오류로 종료합니다.
- 로그가 비밀번호 값을 출력하지 않습니다.
- 무한 restart loop를 만들지 않고 원인을 확인할 수 있습니다.

### 실습 4: 반복 실행

```sh
docker compose restart app
docker compose exec -T db mariadb ... -e 'SELECT COUNT(*) FROM notes;'
```

초기 데이터의 행 수가 증가하지 않아야 합니다.

### 실습 5: 부분 실패

시작 코드의 초기화 과정에서 초기 데이터 입력 직전에 의도적으로 예외를 발생시킵니다.

1. 첫 실행이 실패합니다.
2. DB에 만들어진 테이블을 확인합니다.
3. 예외를 제거합니다.
4. 다시 시작합니다.
5. 초기 데이터가 정확히 한 번 들어가는지 확인합니다.

## 23. 잘못 적용하기 쉬운 부분

### “시작 스크립트는 설치 스크립트입니다”

매 컨테이너 시작마다 실행되는 런타임 수렴 스크립트입니다. 최초 설치만 가정하면 재시작에서 깨집니다.

### “IF NOT EXISTS를 붙이면 모든 스키마 변경이 안전합니다”

열 변경, 데이터 변환, 여러 단계의 스키마 변경에는 버전 관리와 트랜잭션 전략이 필요합니다.

### “depends_on이 있으므로 애플리케이션 재시도는 불필요합니다”

시작 순서를 제어하는 데는 도움이 되지만 실행 중 데이터베이스 재시작과 네트워크 일시 오류는 남습니다.

### “관리자 권한으로 초기화하고 그대로 서비스해도 컨테이너라 괜찮습니다”

컨테이너 격리는 관리자 권한의 위험을 없애지 않습니다. 필요한 초기 작업 뒤 권한을 낮춥니다.

### “비밀값을 환경변수로 내보내면 아무 데도 노출되지 않습니다”

프로세스 환경에 존재합니다. 파일 주입은 Compose 설정과 이미지 노출을 줄이지만 애플리케이션 메모리에는 값이 필요합니다. 로그와 진단 도구 사용을 통제합니다.

## 24. 운영 원칙

- 코드, 설정, 비밀값, 런타임 데이터를 구분합니다.
- 시작 스크립트는 현재 상태를 원하는 상태로 수렴시켜야 합니다.
- 변경 전에 구체적인 상태를 조회합니다.
- 데이터베이스 스키마 변경과 초기 데이터 입력은 재실행과 부분 실패를 고려합니다.
- POSIX sh에서는 `set -eu`, 변수 인용, `"$@"`를 기본으로 합니다.
- 비밀값 파일 경로와 직접 값을 상호 배타적으로 처리합니다.
- 재시도에는 횟수 제한과 실패 메시지가 있어야 합니다.
- 쓰기 경로만 런타임 사용자에게 권한을 줍니다.
- 초기화 뒤 `exec "$@"`로 메인 프로세스에 PID 1을 넘깁니다.
- 상태 검사는 상태를 변경하지 않습니다.

## 공식 문서

- POSIX Shell Command Language: https://pubs.opengroup.org/onlinepubs/9699919799/utilities/V3_chap02.html
- Docker 공식 이미지 시작 명령 관례: https://docs.docker.com/build/building/best-practices/
- PHP PDO: https://www.php.net/manual/en/book.pdo.php
