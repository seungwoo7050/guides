#!/usr/bin/env bash
set -euo pipefail
bin="${1:?}"; a="$(mktemp)"; e="$(mktemp)"; trap 'rm -f "$a" "$e"' EXIT
cat >"$e" <<'OUT'
OK
CONFLICT
BAD_REQUEST
BAD_REQUEST
BYE
OUT
printf 'PUT a 1\nPUT a 2\nGET\nBOGUS\nQUIT\n' | "$bin" >"$a"
diff -u "$e" "$a"
echo '05단계 검사: 통과'
