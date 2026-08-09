#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER=.guide/cloud-computing/prepared.json
export PYTHONDONTWRITEBYTECODE=1

TMP=
TMP_VALIDATED=0
SUMMARY_PRINTED=0

cleanup() {
    status=$?
    trap - 0 HUP INT TERM
    if [ "$TMP_VALIDATED" -eq 1 ] && [ -n "$TMP" ] && [ -d "$TMP" ]; then
        rm -rf -- "$TMP" || status=1
    fi
    if [ "$status" -ne 0 ] && [ "$SUMMARY_PRINTED" -eq 0 ]; then
        printf 'VERIFY SUMMARY: FAIL (prerequisite or interrupted)\n' >&2
    fi
    exit "$status"
}

on_signal() {
    exit 130
}

trap cleanup 0
trap on_signal HUP INT TERM

printf '[verify prerequisite] validating prepare marker and source v2\n'
"$PYTHON" scripts/source_fingerprint.py --check-marker "$MARKER"
source_before=$("$PYTHON" scripts/source_fingerprint.py --scope source)
workspace_before=$("$PYTHON" scripts/source_fingerprint.py --scope workspace)

printf '[verify prerequisite] creating isolated copy outside repository\n'
TMP=$(mktemp -d "${TMPDIR:-/tmp}/guide-cloud-computing.XXXXXX")
"$PYTHON" - "$ROOT" "$TMP" <<'PY'
from __future__ import annotations

import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve(strict=True)
temporary = Path(sys.argv[2]).absolute()
metadata = temporary.lstat()
if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
    raise SystemExit(f'verification temporary path is unsafe: {temporary}')
resolved = temporary.resolve(strict=True)
if resolved == root or root in resolved.parents:
    raise SystemExit(f'verification temporary path must be outside repository: {resolved}')
print(f'isolated-root: {resolved}')
PY
TMP_VALIDATED=1

COPY="$TMP/repository"
ARCHIVE="$TMP/source.tar"
REPORTS="$TMP/reports"
mkdir "$COPY" "$REPORTS"
tar \
    --exclude=.git \
    --exclude=.guide \
    --exclude=.workspace \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*.log' \
    --exclude=.DS_Store \
    -cf "$ARCHIVE" .
tar -xf "$ARCHIVE" -C "$COPY"
rm -f -- "$ARCHIVE"

TOTAL=0
PASSED=0
FAILED=0

run_step() {
    label=$1
    shift
    TOTAL=$((TOTAL + 1))
    printf '[verify %s] START\n' "$label"
    if "$@"; then
        PASSED=$((PASSED + 1))
        printf '[verify %s] PASS\n' "$label"
    else
        FAILED=$((FAILED + 1))
        printf '[verify %s] FAIL\n' "$label" >&2
    fi
}

run_structure() {
    (cd "$COPY" && "$PYTHON" scripts/check_structure.py)
}

run_links() {
    (cd "$COPY" && "$PYTHON" scripts/check_links.py)
}

run_profiles() {
    (cd "$COPY" && "$PYTHON" scripts/check_profiles.py)
}

run_compile_checks() {
    (cd "$COPY" && "$PYTHON" -m compileall -q scripts exercises/07-local-cloud-model)
}

run_reference_report() {
    report="$REPORTS/local-model-report.json"
    (
        cd "$COPY" &&
        "$PYTHON" scripts/verify_cloud_model.py \
            --implementation exercises/07-local-cloud-model/reference/cloud_model.py \
            --report "$report" >/dev/null &&
        cmp "$report" projects/multitenant-document-processing-saas/reference/evidence/local-model-report.json
    )
}

run_step '1/5 structure' run_structure
run_step '2/5 links' run_links
# check_profiles is the single owner of all five mandatory meta-test suites,
# including scripts/test_source_fingerprint.py. Do not run them twice here.
run_step '3/5 profiles+meta-tests' run_profiles
run_step '4/5 compile' run_compile_checks
run_step '5/5 reference-report' run_reference_report

EXPECTED_STEPS=5
if [ "$TOTAL" -ne "$EXPECTED_STEPS" ]; then
    FAILED=$((FAILED + 1))
    printf '[verify mandatory-step-count] FAIL expected=%s actual=%s\n' "$EXPECTED_STEPS" "$TOTAL" >&2
else
    printf '[verify mandatory-step-count] PASS total=%s\n' "$TOTAL"
fi

cd "$ROOT"
printf '[verify integrity] checking original source and learner workspace\n'
source_after=$("$PYTHON" scripts/source_fingerprint.py --scope source)
workspace_after=$("$PYTHON" scripts/source_fingerprint.py --scope workspace)
if [ "$source_before" = "$source_after" ]; then
    printf '[verify source-unchanged] PASS %s\n' "$source_after"
else
    FAILED=$((FAILED + 1))
    printf '[verify source-unchanged] FAIL\nbefore=%s\nafter=%s\n' "$source_before" "$source_after" >&2
fi
if [ "$workspace_before" = "$workspace_after" ]; then
    printf '[verify workspace-unchanged] PASS %s\n' "$workspace_after"
else
    FAILED=$((FAILED + 1))
    printf '[verify workspace-unchanged] FAIL\nbefore=%s\nafter=%s\n' "$workspace_before" "$workspace_after" >&2
fi

if [ "$FAILED" -ne 0 ]; then
    SUMMARY_PRINTED=1
    printf 'VERIFY SUMMARY: FAIL mandatory=%s passed=%s failed=%s source_unchanged=%s workspace_unchanged=%s\n' \
        "$TOTAL" "$PASSED" "$FAILED" \
        "$([ "$source_before" = "$source_after" ] && printf yes || printf no)" \
        "$([ "$workspace_before" = "$workspace_after" ] && printf yes || printf no)" >&2
    exit 1
fi

if ! rm -rf -- "$TMP"; then
    SUMMARY_PRINTED=1
    printf 'VERIFY SUMMARY: FAIL mandatory=%s passed=%s failed=1 cleanup=failed source_unchanged=yes workspace_unchanged=yes\n' \
        "$TOTAL" "$PASSED" >&2
    exit 1
fi
TMP_VALIDATED=0
TMP=

SUMMARY_PRINTED=1
printf 'VERIFY SUMMARY: PASS mandatory=%s passed=%s reports=temp-only source_unchanged=yes workspace_unchanged=yes\n' \
    "$TOTAL" "$PASSED"
