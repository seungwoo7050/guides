#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$root"
marker="$root/.guide/machine-learning/prepared.json"
[ -f "$marker" ] || {
    printf '먼저 ./prepare.sh를 실행하십시오.\n' >&2
    exit 1
}

case ${VERIFY_LOG:-} in
    '') log=$(mktemp /tmp/guide-machine-learning-verify.XXXXXX.log) ;;
    /*) log=$VERIFY_LOG ;;
    *) printf 'VERIFY_LOG는 저장소 밖 절대 경로여야 합니다.\n' >&2; exit 1 ;;
esac
case "$log" in
    "$root"/*) printf 'VERIFY_LOG는 저장소 밖에 있어야 합니다.\n' >&2; exit 1 ;;
esac

temporary=$(mktemp -d /tmp/guide-machine-learning-copy.XXXXXX)
cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    rm -rf -- "$temporary"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

python3 - "$root" "$temporary/repo" <<'PY'
import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
shutil.copytree(
    source,
    destination,
    symlinks=True,
    ignore=shutil.ignore_patterns(
        ".git",
        ".guide",
        "workspace",
        ".workspace.lock",
        ".workspace.tmp.*",
        "__pycache__",
        ".pytest_cache",
        "*.pyc",
        "*.pyo",
    ),
)
PY

before=$(python3 scripts/source-fingerprint.py --root "$root")
expected=$(python3 - "$marker" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["source_sha256"])
PY
)
[ "$before" = "$expected" ] || {
    printf 'prepare 이후 source가 바뀌었습니다. ./prepare.sh를 다시 실행하십시오.\n' >&2
    exit 1
}

(
    set -eu
    cd "$temporary/repo"
    python3 -m unittest discover -s tests -p 'test_*.py'
    python3 scripts/verify-docs.py
    python3 scripts/verify-fixtures.py
    python3 scripts/verify-contracts.py
    python3 scripts/quality-check.py
) >"$log" 2>&1 || {
    cat "$log" >&2
    exit 1
}

after=$(python3 scripts/source-fingerprint.py --root "$root")
[ "$before" = "$after" ] || {
    printf 'verify 과정에서 원본 source가 바뀌었습니다.\n' >&2
    exit 1
}

cat "$log"
printf 'VERIFY OK log=%s source=%s\n' "$log" "$after"
