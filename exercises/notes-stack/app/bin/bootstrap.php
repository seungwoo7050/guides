<?php
declare(strict_types=1);

# [Implementation 4] Application bootstrap input contract
function requiredEnv(string $name): string
{
    $value = getenv($name);
    if ($value === false || $value === '') {
        throw new RuntimeException("{$name} is required");
    }
    return $value;
}

function readSecret(string $path): string
{
    $value = @file_get_contents($path);
    if ($value === false) {
        throw new RuntimeException("secret file is not readable: {$path}");
    }
    $value = preg_replace('/\r?\n\z/', '', $value) ?? '';
    if ($value === '' || str_contains($value, "\r") || str_contains($value, "\n")) {
        throw new RuntimeException("secret file must contain exactly one non-empty line: {$path}");
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
        throw new RuntimeException('database retry configuration is invalid');
    }

    # [Implementation 4-1] Bounded PDO connection retry
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
            if ($attempt < $maxAttempts) {
                usleep($delayMs * 1000);
            }
        }
    }
    if (!$pdo instanceof PDO) {
        throw new RuntimeException(
            sprintf('database did not become ready within %d attempts', $maxAttempts),
            0,
            $lastError
        );
    }

    # [Implementation 4-2] Idempotent application schema
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

    # [Implementation 4-3] Transactional seed marker
    $pdo->beginTransaction();
    try {
        $marker = $pdo->prepare(
            "INSERT IGNORE INTO app_meta (meta_key, meta_value) VALUES ('seed_v1', 'done')"
        );
        $marker->execute();
        if ($marker->rowCount() === 1) {
            $seed = $pdo->prepare('INSERT INTO notes (body) VALUES (:body)');
            $seed->execute(['body' => 'seed note']);
            fwrite(STDERR, "seed data inserted\n");
        } else {
            fwrite(STDERR, "seed data already present\n");
        }
        $pdo->commit();
    } catch (Throwable $error) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        throw $error;
    }
}

try {
    runBootstrap();
} catch (Throwable $error) {
    fwrite(STDERR, "application bootstrap failed: {$error->getMessage()}\n");
    exit(1);
}
