#!/bin/sh
set -eu

base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
for scenario in \
    wrong-db-host \
    wrong-db-password \
    missing-secret \
    wrong-fcgi-port \
    broken-healthcheck \
    data-loss
do
    "$base_dir/run-scenario.sh" "$scenario"
done
echo "통과: 문제 해결 시나리오 6개"
