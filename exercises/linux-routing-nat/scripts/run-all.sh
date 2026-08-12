#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# [Implementation 7] 세 공개 실험을 독립 cleanup 경계로 순서대로 실행합니다.
"$SCRIPT_DIR/run-routing.sh"
"$SCRIPT_DIR/run-nat.sh"
"$SCRIPT_DIR/run-loss-retransmission.sh"
