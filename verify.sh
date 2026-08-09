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
    '') log=$(mktemp /tmp/guide-machine-learning-verify.log.XXXXXX) ;;
    /*)
        log=$VERIFY_LOG
        python3 - "$log" "$root" <<'PY'
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
root = Path(sys.argv[2]).resolve()
if path.exists() or path.is_symlink():
    raise SystemExit(f"VERIFY_LOG가 이미 존재합니다: {path}")
parent = path.parent.resolve()
try:
    parent.relative_to(root)
except ValueError:
    pass
else:
    raise SystemExit("VERIFY_LOG는 저장소 밖에 있어야 합니다.")
if not parent.is_dir():
    raise SystemExit(f"VERIFY_LOG 상위 디렉터리가 없습니다: {parent}")
descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(descriptor)
PY
        ;;
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

before=$(python3 scripts/repo-state.py --root "$root")
expected=$(python3 - "$marker" <<'PY'
import json
import sys
from pathlib import Path
print(json.dumps(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["state"], ensure_ascii=False, sort_keys=True))
PY
)
[ "$before" = "$expected" ] || {
    printf 'prepare 이후 HEAD·source·index 또는 workspace가 바뀌었습니다. ./prepare.sh를 다시 실행하십시오.\n' >&2
    exit 1
}

(
    set -eu
    cd "$temporary/repo"
    sh -n prepare.sh verify.sh scripts/new-workspace.sh
    python3 -m compileall -q scripts tests examples exercises/model-lifecycle/reference exercises/modern-model-release
    python3 scripts/run-with-limits.py --seconds 60 --cpu-seconds 45 -- \
        python3 -m unittest discover -s tests -p 'test_*.py'
    python3 scripts/run-with-limits.py --seconds 30 --cpu-seconds 20 -- \
        python3 scripts/verify-docs.py
    python3 scripts/run-with-limits.py --seconds 30 --cpu-seconds 20 -- \
        python3 scripts/verify-fixtures.py
    python3 scripts/run-with-limits.py --seconds 30 --cpu-seconds 20 -- \
        python3 scripts/verify-contracts.py
    PYTHONPATH=exercises/model-lifecycle/reference/src \
        python3 scripts/run-with-limits.py --seconds 60 --cpu-seconds 45 -- \
        python3 -m unittest discover -s exercises/model-lifecycle/reference/tests -p 'test_*.py'
    python3 scripts/run-with-limits.py --seconds 30 --cpu-seconds 20 -- \
        python3 scripts/check-submission.py --workspace exercises/model-lifecycle/reference --stage 8
    python3 scripts/run-with-limits.py --seconds 60 --cpu-seconds 45 -- \
        python3 exercises/modern-model-release/tests/check.py \
        --candidate exercises/modern-model-release/reference
    python3 scripts/run-with-limits.py --seconds 120 --cpu-seconds 90 -- \
        python3 scripts/quality-check.py
) >>"$log" 2>&1 || {
    cat "$log" >&2
    exit 1
}

after=$(python3 scripts/repo-state.py --root "$root")
[ "$before" = "$after" ] || {
    printf 'verify 과정에서 원본 HEAD·source·index 또는 workspace가 바뀌었습니다.\n' >&2
    exit 1
}

cat "$log"
source_hash=$(python3 - "$after" <<'PY'
import json
import sys
print(json.loads(sys.argv[1])["source_sha256"])
PY
)
printf 'VERIFY OK log=%s source=%s\n' "$log" "$source_hash"
