#!/usr/bin/env bash
set -euo pipefail
bin="${1:?}"
[[ "$($bin '3 4 + 2 *')" == '14' ]]
[[ "$($bin '10 3 - 2 /')" == '3' ]]
! "$bin" '1 +' >/dev/null 2>&1
! "$bin" '4 0 /' >/dev/null 2>&1
! "$bin" '1 2' >/dev/null 2>&1
echo 'rpn 검사: 통과'
