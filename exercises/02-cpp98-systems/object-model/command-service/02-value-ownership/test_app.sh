#!/usr/bin/env bash
set -euo pipefail
bin="${1:?binary required}"
actual="$(mktemp)"; expected="$(mktemp)"
trap 'rm -f "$actual" "$expected"' EXIT
cat >"$expected" <<'OUT'
OK
VALUE alice
BYE
OUT
printf 'PUT name alice\nGET name\nQUIT\n' | "$bin" >"$actual"
diff -u "$expected" "$actual"
printf '02단계 프로그램 검사: 통과\n'
