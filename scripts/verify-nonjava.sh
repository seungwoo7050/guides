#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
RELEASE="$ROOT/exercises/04-release-and-evidence/01-release-manifest"
KRAFT="$ROOT/exercises/90-optional-labs/single-broker-kraft"
WORK_ROOT="${GUIDE_VERIFY_WORK_DIR:-$ROOT/.guide/verify}/nonjava"

rm -rf -- "$WORK_ROOT"
mkdir -p -- "$WORK_ROOT"

python3 "$RELEASE/tests/verify_manifest.py" \
  "$RELEASE/reference/manifest_check.py"
printf '[PASS] release manifest reference\n'

set +e
python3 "$RELEASE/tests/verify_manifest.py" \
  "$RELEASE/skeleton/manifest_check.py" \
  >"$WORK_ROOT/release-skeleton.log" 2>&1
status=$?
set -e
if [[ $status -eq 0 ]]; then
  printf 'release manifest skeleton unexpectedly passed\n' >&2
  exit 1
fi
release_failure='GUIDE_SEMANTIC: invalid manifest was accepted (expected duplicate)'
if ! python3 - "$WORK_ROOT/release-skeleton.log" "$release_failure" <<'PY'
from pathlib import Path
import sys

lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()
expected = "AssertionError: " + sys.argv[2]
assertions = [line for line in lines if line.startswith("AssertionError:")]
if assertions != [expected]:
    raise SystemExit(1)
PY
then
  printf 'release manifest skeleton failed for an unintended reason\n' >&2
  cat "$WORK_ROOT/release-skeleton.log" >&2
  exit 1
fi
printf '[PASS] expected release manifest skeleton failure\n'

if [[ "${GUIDE_VALIDATOR_SELF_TEST:-}" == "release" ]]; then
  exit 0
fi

"$KRAFT/verify.sh" --static
printf '[PASS] KRaft static contract\n'

[[ "${GUIDE_DOCKER_READY:-0}" == "1" ]] || {
  printf 'strict verification requires prepared Docker integration\n' >&2
  exit 2
}
"$KRAFT/verify.sh"
printf '[PASS] KRaft Docker integration\n'
