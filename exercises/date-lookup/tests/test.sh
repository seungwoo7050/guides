#!/usr/bin/env bash
set -euo pipefail
bin="$(realpath "${1:?}")"
root="$(cd "$(dirname "$0")/.." && pwd)"
actual="$(mktemp)"; expected="$(mktemp)"; trap 'rm -f "$actual" "$expected"' EXIT
cat >"$expected" <<'OUT'
2024-01-05 => 4 = 8
2024-01-12 => 2 = 7
error: no rate before 2023-12-31
error: invalid date
error: amount out of range
error: invalid input
OUT
printf '2024-01-05 | 4\n2024-01-12 | 2\n2023-12-31 | 1\n2024-02-30 | 1\n2024-01-01 | 1001\n2024-01-01 | nan\n' | "$bin" "$root/data.csv" >"$actual"
diff -u "$expected" "$actual"
