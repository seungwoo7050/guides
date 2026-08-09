#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

if [ ! -f .guide/platform-engineering/prepared.json ]; then
  echo '먼저 ./prepare.sh를 실행하십시오.' >&2
  exit 1
fi

python3 scripts/verify_repository.py --full
