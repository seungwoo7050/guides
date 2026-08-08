#!/bin/sh
set -eu

command=${1:-}
workdir=${2:-}
hostname=${3:-}
value=${4:-}

if [ -z "$command" ] || [ -z "$workdir" ] || [ -z "$hostname" ] || [ -z "$value" ]; then
    echo "사용법: $0 {issue|renew|verify} WORKDIR HOSTNAME VALUE" >&2
    exit 2
fi

case "$command" in
  issue|renew|verify)
    echo "TODO: $command $workdir $hostname" >&2
    exit 1
    ;;
  *)
    echo "알 수 없는 명령: $command" >&2
    exit 2
    ;;
esac
