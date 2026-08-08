#!/usr/bin/env bash
set -euo pipefail
bin="${1:?}"
out="$($bin 9 3 7 1 8 2 6 5 4 3)"
grep -Fx '정렬 후: 1 2 3 3 4 5 6 7 8 9' <<<"$out" >/dev/null
! "$bin" 1 nope 2 >/dev/null 2>&1
! "$bin" -1 2 >/dev/null 2>&1
echo 'sorter 검사: 통과'
