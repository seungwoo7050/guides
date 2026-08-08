#!/usr/bin/env bash
set -euo pipefail
bin="${1:?}"; a="$(mktemp)"; e="$(mktemp)"; trap 'rm -f "$a" "$e"' EXIT
cat >"$e" <<'OUT'
2024-01-05 => 4 = 8
2024-01-12 => 2 = 7
오류: 2023-12-31 이전의 환율이 없습니다
오류: 날짜가 올바르지 않습니다
오류: 금액이 허용 범위를 벗어났습니다
OUT
printf '2024-01-05 | 4\n2024-01-12 | 2\n2023-12-31 | 1\n2024-02-30 | 1\n2024-01-01 | 1001\n' | "$bin" "$PWD/data.csv" >"$a"
diff -u "$e" "$a"
echo 'date-lookup 검사: 통과'
