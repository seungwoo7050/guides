# PHP와 PDO 애플리케이션 초기화 기초

이 문서는 [멱등한 애플리케이션 초기화](../docs/06-idempotent-app-bootstrap.md)를 읽기 위해 필요한 PHP 실행 방식, 환경 변수, 비밀값 파일, PDO와 트랜잭션의 최소 모델을 설명합니다. 별도 Compose 스택을 만들지 않고 저장소의 [애플리케이션 초기화 실습](../exercises/06-app-bootstrap/README.md)을 사용합니다.

## PHP CLI와 PHP-FPM의 역할을 나눕니다

PHP CLI는 명령을 한 번 실행하고 종료합니다. 실습의 `bootstrap.php`처럼 데이터베이스 준비 작업에 알맞습니다. PHP-FPM은 여러 요청을 계속 기다리는 장기 실행 프로세스입니다.

초기화 CLI와 PHP-FPM을 어떤 순서로 연결하는지는 [멱등한 애플리케이션 초기화](../docs/06-idempotent-app-bootstrap.md)에서 다룹니다. 여기서는 두 실행 방식의 수명이 다르고, 초기화 코드는 성공과 실패를 종료 코드로 구분해야 한다는 점만 기억합니다.

PHP 파일은 엄격한 타입 선언으로 시작합니다.

```php
<?php
declare(strict_types=1);
```

`strict_types=1`은 함수 호출의 scalar type coercion을 엄격하게 할 뿐, 환경 변수나 파일 내용을 자동으로 검증하지 않습니다. 외부 입력은 별도로 빈 값, 형식과 범위를 검사합니다.

호스트에 PHP CLI가 있다면 저장소 루트에서 문법만 빠르게 확인할 수 있습니다.

```sh
php -l web-infrastructure/exercises/06-app-bootstrap/reference/app/bin/bootstrap.php
```

## 환경 변수는 `string|false`입니다

`getenv()`는 값이 있으면 문자열, 없으면 `false`를 반환합니다. 문자열 `"0"`은 유효한 값일 수 있으므로 truthy 검사로 누락을 판단하지 않습니다.

```php
function requiredEnv(string $name): string
{
    $value = getenv($name);
    if ($value === false || $value === '') {
        throw new RuntimeException("{$name} 환경 변수가 필요합니다.");
    }
    return $value;
}
```

정수 설정은 문자열 상태로 계산에 사용하지 않고 변환과 범위 검사를 함께 수행합니다.

```php
function integerEnv(string $name, int $default, int $min, int $max): int
{
    $raw = getenv($name);
    if ($raw === false) {
        return $default;
    }
    $value = filter_var(
        $raw,
        FILTER_VALIDATE_INT,
        ['options' => ['min_range' => $min, 'max_range' => $max]]
    );
    if ($value === false) {
        throw new RuntimeException("{$name} 값의 범위가 올바르지 않습니다.");
    }
    return $value;
}
```

오류에는 변수 이름과 요구 조건을 기록하되 비밀번호 같은 실제 값은 포함하지 않습니다.

## 비밀값은 경로와 내용을 각각 검증합니다

환경 변수에는 비밀값 자체가 아니라 Docker secret 파일의 경로를 전달합니다. 파일을 읽을 수 있는지, 비어 있지 않은지, 단일 행인지 확인합니다.

많은 secret 파일은 마지막에 LF 또는 CRLF 한 개를 포함합니다. `trim()`은 앞뒤 공백까지 바꾸고 `rtrim($value, "\r\n")`은 여러 줄 끝 문자를 모두 지우므로 비밀값 계약을 흐립니다. 정확히 한 개의 줄 끝만 제거한 뒤 남은 줄 바꿈은 거부합니다.

```php
function readSecret(string $path): string
{
    $value = @file_get_contents($path);
    if ($value === false) {
        throw new RuntimeException("비밀값 파일을 읽을 수 없습니다: {$path}");
    }

    if (str_ends_with($value, "\r\n")) {
        $value = substr($value, 0, -2);
    } elseif (str_ends_with($value, "\n")) {
        $value = substr($value, 0, -1);
    }

    if ($value === '') {
        throw new RuntimeException("비밀값 파일이 비어 있습니다: {$path}");
    }
    if (str_contains($value, "\r") || str_contains($value, "\n")) {
        throw new RuntimeException("비밀값 파일은 한 줄이어야 합니다: {$path}");
    }
    return $value;
}
```

로그에는 파일 경로, 검증 단계와 오류 종류만 남깁니다. secret의 일부를 잘라 출력하거나 실패 확인을 위해 복사본을 만들지 않습니다.

## 오류는 원래 원인을 보존해 전달합니다

PHP의 `Throwable`은 `Exception`과 `Error`를 함께 포함합니다. 최상위 초기화 코드는 오류를 stderr에 기록하고 non-zero로 종료할 수 있지만, 하위 함수는 대개 원래 예외를 다시 던져 호출자가 정책을 정하게 합니다.

```php
try {
    runBootstrap();
} catch (Throwable $error) {
    fwrite(STDERR, "애플리케이션 초기화에 실패했습니다.\n");
    exit(1);
}
```

운영 로그에 stack trace나 DSN 전체를 무조건 출력하지 않습니다. PDO 오류에는 host, 사용자 이름이나 query parameter가 들어갈 수 있으므로 공개 범위를 정합니다.

## PDO 연결 설정은 실패를 예외로 만듭니다

MariaDB 연결 DSN과 PDO 옵션은 다음 역할을 가집니다.

```php
$dsn = sprintf(
    'mysql:host=%s;dbname=%s;charset=utf8mb4',
    requiredEnv('DB_HOST'),
    requiredEnv('DB_NAME')
);

$pdo = new PDO($dsn, requiredEnv('DB_USER'), $password, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES => false,
]);
```

- `ERRMODE_EXCEPTION`: 연결과 SQL 실패를 예외로 처리합니다.
- `FETCH_ASSOC`: 열 이름으로 결과를 읽습니다.
- `EMULATE_PREPARES=false`: 가능한 경우 driver의 prepared statement를 사용합니다.

## 값은 prepared statement로 전달합니다

외부 값을 SQL 문자열에 이어 붙이지 않습니다.

```php
$statement = $pdo->prepare(
    'INSERT INTO notes (body) VALUES (:body)'
);
$statement->execute(['body' => $body]);
```

placeholder는 값에만 사용할 수 있습니다. 테이블명, 열 이름과 정렬 방향 같은 식별자가 동적이라면 허용 목록에서 SQL 조각을 선택합니다.

```php
$orders = [
    'newest' => 'created_at DESC',
    'oldest' => 'created_at ASC',
];
$orderBy = $orders[$requestedOrder] ?? $orders['newest'];
$rows = $pdo->query("SELECT id, body FROM notes ORDER BY {$orderBy}")->fetchAll();
```

## 기본 트랜잭션은 성공과 실패를 한 경계로 묶습니다

서로 함께 성공하거나 실패해야 하는 쓰기는 transaction으로 묶습니다.

```php
$pdo->beginTransaction();
try {
    $statement = $pdo->prepare(
        'INSERT INTO notes (body) VALUES (:body)'
    );
    $statement->execute(['body' => $body]);
    $pdo->commit();
} catch (Throwable $error) {
    try {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
    } catch (Throwable $rollbackError) {
        error_log('rollback에도 실패했습니다.');
    }
    throw $error;
}
```

rollback 실패가 최초 오류를 가리지 않게 하고, 호출자에게는 원래 오류를 다시 전달합니다. DDL의 transaction 지원 여부는 데이터베이스마다 다르므로 이 예제를 schema migration에 그대로 적용하지 않습니다.

## 초기화 정책은 6장으로 이어집니다

연결 재시도, schema 준비, 고유 seed marker, 부분 실패와 entrypoint의 `exec`는 [멱등한 애플리케이션 초기화](../docs/06-idempotent-app-bootstrap.md)에서 함께 다룹니다. 구현은 [애플리케이션 초기화 실습](../exercises/06-app-bootstrap/README.md)의 `skeleton`과 `reference`로 비교하세요.

## PHP·PDO 원문

- [PHP: 엄격한 타입 선언](https://www.php.net/manual/en/language.types.declarations.php)
- [PHP: PDO](https://www.php.net/manual/en/book.pdo.php)
- [PHP: PDO transaction](https://www.php.net/manual/en/pdo.transactions.php)
- [PHP: `getenv`](https://www.php.net/manual/en/function.getenv.php)
