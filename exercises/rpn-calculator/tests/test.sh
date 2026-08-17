#!/usr/bin/env bash
set -euo pipefail
bin="$(realpath "${1:?}")"
[[ "$($bin '3 4 + 2 *')" == '14' ]]
[[ "$($bin '10 3 - 2 /')" == '3' ]]
[[ "$($bin '-3 -4 *')" == '12' ]]
! "$bin" '1 +' >/dev/null 2>&1
! "$bin" '4 0 /' >/dev/null 2>&1
! "$bin" '1 2' >/dev/null 2>&1
! "$bin" '2147483647 1 +' >/dev/null 2>&1
! "$bin" '-2147483648 -1 *' >/dev/null 2>&1
