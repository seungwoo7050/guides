<?php
declare(strict_types=1);

// [Implementation 2] 환경과 file secret을 business initialization 전에 검증합니다.
function requiredEnv(string $name): string
{
    $value = getenv($name);
    if ($value === false || $value === '') {
        throw new RuntimeException("{$name} 환경 변수가 필요합니다.");
    }
    return $value;
}

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

function runBootstrap(): void
{
    $host = requiredEnv('DB_HOST');
    $name = requiredEnv('DB_NAME');
    $user = requiredEnv('DB_USER');
    $password = readSecret(requiredEnv('DB_PASSWORD_FILE'));
    $dsn = "mysql:host={$host};dbname={$name};charset=utf8mb4";

    $maxAttempts = (int)(getenv('DB_CONNECT_ATTEMPTS') ?: '60');
    $delayMs = (int)(getenv('DB_CONNECT_DELAY_MS') ?: '500');
    if ($maxAttempts < 1 || $maxAttempts > 600 || $delayMs < 0 || $delayMs > 10_000) {
        throw new RuntimeException('데이터베이스 재시도 설정이 올바르지 않습니다.');
    }

    // [Implementation 3] 연결 소유권을 bounded retry 안에 두어 영구 대기를 실패로 바꿉니다.
    $pdo = null;
    $lastError = null;
    for ($attempt = 1; $attempt <= $maxAttempts; $attempt++) {
        try {
            $pdo = new PDO($dsn, $user, $password, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false,
            ]);
            break;
        } catch (PDOException $error) {
            $lastError = $error;
            usleep($delayMs * 1000);
        }
    }
    if (!$pdo instanceof PDO) {
        throw new RuntimeException(
            sprintf('데이터베이스가 %d회 안에 준비되지 않았습니다.', $maxAttempts),
            0,
            $lastError
        );
    }

    // [Implementation 4] schema를 재실행 가능한 선언으로 준비합니다.
    $pdo->exec(<<<'SQL'
CREATE TABLE IF NOT EXISTS app_meta (
    meta_key VARCHAR(100) PRIMARY KEY,
    meta_value VARCHAR(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
SQL);
    $pdo->exec(<<<'SQL'
CREATE TABLE IF NOT EXISTS notes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    body VARCHAR(500) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
SQL);

    // [Implementation 5] marker 획득과 seed insert를 같은 transaction으로 묶습니다.
    $pdo->beginTransaction();
    try {
        $marker = $pdo->prepare(
            "INSERT IGNORE INTO app_meta (meta_key, meta_value) VALUES ('seed_v1', 'done')"
        );
        $marker->execute();
        if ($marker->rowCount() === 1) {
            $seed = $pdo->prepare('INSERT INTO notes (body) VALUES (:body)');
            $seed->execute(['body' => 'seed note']);
            fwrite(STDERR, "초기 애플리케이션 데이터를 추가했습니다.\n");
        } else {
            fwrite(STDERR, "초기 애플리케이션 데이터가 이미 있어 건너뜁니다.\n");
        }
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
}

try {
    runBootstrap();
} catch (Throwable $error) {
    $reason = $error instanceof RuntimeException
        ? $error->getMessage()
        : '예상하지 못한 오류가 발생했습니다.';
    fwrite(STDERR, "애플리케이션 초기화에 실패했습니다: {$reason}\n");
    exit(1);
}
