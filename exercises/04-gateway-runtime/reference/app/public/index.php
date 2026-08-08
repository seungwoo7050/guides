<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

echo json_encode([
    'status' => 'ok',
    'runtime' => 'php-fpm',
    'script' => __FILE__,
    'https' => $_SERVER['HTTPS'] ?? null,
    'request_method' => $_SERVER['REQUEST_METHOD'] ?? null,
], JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT), "\n";
