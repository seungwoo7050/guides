#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$script_dir"
python=${PYTHON:-python3}

require_python() {
    command -v "$python" >/dev/null 2>&1 || {
        printf 'FAIL: python3가 필요합니다.\n' >&2
        exit 1
    }
}

check_reference() {
    "$python" check_answers.py reference/diagnoses.json
}

check_skeleton_contract() {
    tmp=$(mktemp "${TMPDIR:-/tmp}/unix-guide-skeleton.XXXXXX")
    if "$python" check_answers.py skeleton/diagnoses.json >"$tmp" 2>&1; then
        cat "$tmp" >&2
        rm -f "$tmp"
        printf 'FAIL: skeleton이 완성 답안으로 통과했습니다.\n' >&2
        exit 1
    fi
    if ! grep -q 'TODO\|누락\|필요' "$tmp"; then
        cat "$tmp" >&2
        rm -f "$tmp"
        printf 'FAIL: skeleton 거부 이유가 예상한 계약 오류가 아닙니다.\n' >&2
        exit 1
    fi
    rm -f "$tmp"
    printf 'PASS skeleton contract\n'
}

check_quality() {
    tmp=$(mktemp "${TMPDIR:-/tmp}/unix-guide-broken.XXXXXX")
    if "$python" check_answers.py tests/broken-diagnoses.json >"$tmp" 2>&1; then
        cat "$tmp" >&2
        rm -f "$tmp"
        printf 'FAIL: 알려진 잘못된 답안이 통과했습니다.\n' >&2
        exit 1
    fi
    if ! grep -q '누락된 사례\|이어야 합니다' "$tmp"; then
        cat "$tmp" >&2
        rm -f "$tmp"
        printf 'FAIL: 오답 거부 이유가 충분하지 않습니다.\n' >&2
        exit 1
    fi
    rm -f "$tmp"
    printf 'PASS checker quality\n'
}

check_scenarios() {
    "$python" lab.py selftest
}

check_workspace() {
    test -f workspace/diagnoses.json || {
        printf 'FAIL: 먼저 ./create-workspace.sh를 실행하십시오.\n' >&2
        exit 1
    }
    "$python" check_answers.py workspace/diagnoses.json
}

require_python
case "${1:-all}" in
    reference)
        check_reference
        ;;
    skeleton)
        check_skeleton_contract
        ;;
    quality)
        check_quality
        ;;
    scenarios)
        check_scenarios
        ;;
    workspace)
        check_workspace
        ;;
    all)
        check_reference
        check_skeleton_contract
        check_quality
        check_scenarios
        ;;
    *)
        printf '사용법: %s {reference|skeleton|quality|scenarios|workspace|all}\n' "$0" >&2
        exit 2
        ;;
esac
