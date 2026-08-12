<?php
declare(strict_types=1);

// [Implementation 1] FastCGI가 실행할 최소 request/response 계약을 먼저 고정합니다.
header('Content-Type: application/json; charset=utf-8');

echo json_encode([
    'status' => 'ok',
    'runtime' => 'php-fpm',
    'script' => __FILE__,
    'https' => $_SERVER['HTTPS'] ?? null,
    'request_method' => $_SERVER['REQUEST_METHOD'] ?? null,
], JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT), "\n";
