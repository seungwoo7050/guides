#!/usr/bin/env bash
set -euo pipefail
bin="${1:?}"
out="$($bin ./helpers/echo_cgi.py 1000 'hello cgi')"
grep -F 'Status: 200' <<<"$out" >/dev/null
grep -F 'HELLO CGI' <<<"$out" >/dev/null
echo 'CGI 프로세스 검사: 통과'
