#!/bin/sh
set -u

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python3}
MODE=${1:-all}
FAILED=0
OUTPUT_DIR=""

case "$MODE" in
    all|static|meta|foundations|production|repeatability) ;;
    *)
        echo "사용법: $0 [all|static|meta|foundations|production|repeatability]" >&2
        exit 2
        ;;
esac

export PYTHONDONTWRITEBYTECODE=1
OUTPUT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/guide-web-infra-suite.XXXXXX") || exit 2

cleanup()
{
    rm -rf "$OUTPUT_DIR"
}

on_signal()
{
    signal=$1
    trap - EXIT HUP INT TERM
    cleanup
    case "$signal" in
        HUP) exit 129 ;;
        INT) exit 130 ;;
        TERM) exit 143 ;;
    esac
}

trap cleanup EXIT
trap 'on_signal HUP' HUP
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM

run_pass()
{
    label=$1
    shift
    output="$OUTPUT_DIR/pass-$$.log"

    if "$@" >"$output" 2>&1
    then
        printf '[PASS] %s\n' "$label"
        cat "$output"
    else
        status=$?
        printf '[FAIL] %s (exit=%d)\n' "$label" "$status" >&2
        cat "$output" >&2
        FAILED=1
    fi
    rm -f "$output"
}

expect_failure()
{
    label=$1
    shift
    output="$OUTPUT_DIR/reject-$$.log"

    "$@" >"$output" 2>&1
    status=$?

    if [ "$status" -eq 1 ] &&
       grep -Eqi '실패|오류|거부|허용하지|TODO' "$output" &&
       ! grep -Eqi \
          'Traceback|ModuleNotFoundError|ImportError|command not found|Permission denied|Cannot connect to the Docker daemon|error during connect|failed to solve|no such service' \
          "$output"
    then
        printf '[PASS] %s: 미완성 상태를 올바르게 거부했습니다.\n' "$label"
        cat "$output"
    else
        printf '[FAIL] %s: 기대한 계약 실패가 아닙니다 (exit=%d).\n' \
            "$label" "$status" >&2
        cat "$output" >&2
        FAILED=1
    fi
    rm -f "$output"
}

run_static()
{
    run_pass "static verifier" "$PYTHON" -B "$ROOT/scripts/static-verify.py"
}

run_meta()
{
    run_pass "static verifier meta-tests" "$PYTHON" -B "$ROOT/scripts/meta-verify.py"
}

run_foundations()
{
    for exercise in \
        01-request-and-process \
        02-container \
        03-compose \
        04-gateway-runtime \
        05-database \
        06-app-bootstrap
    do
        run_pass "$exercise reference" \
            "$ROOT/exercises/$exercise/verify.sh" reference
        expect_failure "$exercise skeleton" \
            "$ROOT/exercises/$exercise/verify.sh" skeleton
    done

    run_pass "07-troubleshooting scenarios" \
        "$ROOT/exercises/07-troubleshooting/verify.sh"
}

run_production()
{
    for exercise in \
        08-production-contract \
        09-host-hardening \
        10-public-tls \
        11-release-artifact \
        12-deployment-rollback \
        13-secret-rotation \
        14-observability \
        15-disaster-recovery \
        16-capacity-and-updates \
        17-incident-response \
        18-production-rebuild
    do
        run_pass "$exercise reference" \
            "$ROOT/exercises/$exercise/verify.sh" reference
        expect_failure "$exercise skeleton" \
            "$ROOT/exercises/$exercise/verify.sh" skeleton
    done
}

run_repeatability()
{
    # 상태와 자원을 다루는 대표 실습을 같은 run id에서 다시 실행합니다.
    # 첫 실행의 container, volume, 임시 파일 또는 pointer가 남으면 두 번째
    # 실행이 실패하므로 cleanup과 멱등성을 함께 확인할 수 있습니다.
    for exercise in \
        03-compose \
        05-database \
        06-app-bootstrap \
        10-public-tls \
        12-deployment-rollback \
        13-secret-rotation \
        15-disaster-recovery \
        18-production-rebuild
    do
        run_pass "$exercise repeatability reference" \
            "$ROOT/exercises/$exercise/verify.sh" reference
    done
}

case "$MODE" in
    static) run_static ;;
    meta) run_meta ;;
    foundations) run_foundations ;;
    production) run_production ;;
    repeatability) run_repeatability ;;
    all)
        run_static
        run_meta
        run_foundations
        run_production
        run_repeatability
        ;;
esac

if [ "$FAILED" -eq 0 ]
then
    printf '검증 suite 통과: %s\n' "$MODE"
    exit 0
fi

printf '검증 suite 실패: %s\n' "$MODE" >&2
exit 1
