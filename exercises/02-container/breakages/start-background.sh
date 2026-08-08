#!/bin/sh
set -eu
python /app/server.py &
echo "서버를 백그라운드로 보냈으므로 PID 1이 곧 종료됩니다." >&2
