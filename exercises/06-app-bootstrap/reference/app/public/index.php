<?php
declare(strict_types=1);

function envRequired(string $name): string
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

// [Implementation 8] request process가 공유하는 PDO와 secret 읽기 경계를 한 함수가 소유합니다.
function db(): PDO
{
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }
    $password = readSecret(envRequired('DB_PASSWORD_FILE'));
    $dsn = sprintf(
        'mysql:host=%s;dbname=%s;charset=utf8mb4',
        envRequired('DB_HOST'),
        envRequired('DB_NAME')
    );
    $pdo = new PDO($dsn, envRequired('DB_USER'), $password, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    return $pdo;
}

function jsonResponse(array $payload, int $status = 200): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
    exit;
}

// [Implementation 9] public route·validation·prepared write를 마지막 사용자 계약으로 연결합니다.
try {
    $path = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH) ?: '/';
    $method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

    if ($path === '/health') {
        db()->query('SELECT 1')->fetchColumn();
        jsonResponse(['status' => 'ok', 'database' => 'ok']);
    }

    if ($path === '/api/notes' && $method === 'GET') {
        $rows = db()->query('SELECT id, body, created_at FROM notes ORDER BY id')->fetchAll();
        jsonResponse(['notes' => $rows]);
    }

    if ($path === '/api/notes' && $method === 'POST') {
        $input = json_decode(file_get_contents('php://input') ?: '{}', true, 512, JSON_THROW_ON_ERROR);
        $body = trim((string)($input['body'] ?? ''));
        if ($body === '' || strlen($body) > 500) {
            jsonResponse(['error' => '본문은 1자 이상 500자 이하여야 합니다.'], 400);
        }
        $statement = db()->prepare('INSERT INTO notes (body) VALUES (:body)');
        $statement->execute(['body' => $body]);
        jsonResponse(['id' => (int)db()->lastInsertId(), 'body' => $body], 201);
    }

    if ($path !== '/') {
        jsonResponse(['error' => '요청한 경로를 찾을 수 없습니다.'], 404);
    }

    $count = (int)db()->query('SELECT COUNT(*) FROM notes')->fetchColumn();
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><title>웹 인프라 실습</title>';
    echo '<h1>애플리케이션이 실행 중입니다.</h1>';
    echo '<p>저장된 메모: ' . $count . '</p>';
} catch (Throwable $error) {
    error_log('요청 처리에 실패했습니다: ' . $error::class);
    jsonResponse(['error' => '서버 내부 오류가 발생했습니다.'], 500);
}
