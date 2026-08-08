#!/bin/sh
set -u
GIT_OPTIONAL_LOCKS=0
export GIT_OPTIONAL_LOCKS
PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

GUIDE_ID=computer-networks
ROOT=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
STATE_FILE="$ROOT/.guide/$GUIDE_ID/prepared.json"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERIFY_LOG=${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-computer-networks-verify-${TIMESTAMP}-$$.log}
RUN_ID="computer-networks-${TIMESTAMP}-$$"
RUN_DIR=
WORK_TREE=
PASS_COUNT=0
FAIL_COUNT=0
FINISHED=0
LOG_READY=0
STEP_PID=

preflight_die()
{
    FINISHED=1
    if [ "$LOG_READY" -eq 1 ]; then
        {
            printf 'verify 실패: %s\n' "$*"
            printf 'passed=0 failed=1 skipped=0\n'
            printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
            printf 'RESULT: FAIL\n'
        } | tee -a "$VERIFY_LOG" >&2
    else
        printf 'verify 실패: %s\n' "$*" >&2
        printf 'passed=0 failed=1 skipped=0\n' >&2
        printf 'VERIFY LOG: %s\n' "$VERIFY_LOG" >&2
        printf 'RESULT: FAIL\n' >&2
    fi
    exit 2
}

case "$VERIFY_LOG" in
    /*) ;;
    *) preflight_die 'VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다.' ;;
esac
mkdir -p -- "$(dirname "$VERIFY_LOG")" 2>/dev/null || preflight_die '로그 디렉터리를 만들 수 없습니다.'
log_directory=$(CDPATH= cd "$(dirname "$VERIFY_LOG")" && pwd -P) || preflight_die '로그 디렉터리를 확인할 수 없습니다.'
VERIFY_LOG="$log_directory/$(basename "$VERIFY_LOG")"
case "$VERIFY_LOG" in
    "$ROOT"|"$ROOT"/*) preflight_die 'VERIFY_LOG는 저장소 밖이어야 합니다.' ;;
esac
[ ! -L "$VERIFY_LOG" ] || preflight_die 'VERIFY_LOG symlink는 허용하지 않습니다.'
: >"$VERIFY_LOG" || preflight_die 'VERIFY_LOG를 쓸 수 없습니다.'
LOG_READY=1

emit()
{
    printf '%s\n' "$*" | tee -a "$VERIFY_LOG"
}

cleanup()
{
    status=$?
    trap - EXIT HUP INT TERM
    if command -v docker >/dev/null 2>&1; then
        docker ps -aq --filter "label=guide.computer-networks.verify=$RUN_ID" 2>/dev/null |
            while IFS= read -r container; do
                [ -z "$container" ] || docker rm -f "$container" >/dev/null 2>&1 || true
            done
    fi
    [ -z "${RUN_DIR:-}" ] || rm -rf -- "$RUN_DIR"
    if [ "$FINISHED" -eq 0 ]; then
        emit 'Verification summary'
        emit "passed=$PASS_COUNT failed=$FAIL_COUNT skipped=0"
        emit "VERIFY LOG: $VERIFY_LOG"
        emit 'RESULT: FAIL'
    fi
    exit "$status"
}
stop_on_signal()
{
    code=$1
    trap - HUP INT TERM
    if [ -n "${STEP_PID:-}" ]; then
        kill -TERM "$STEP_PID" >/dev/null 2>&1 || true
        wait "$STEP_PID" >/dev/null 2>&1 || true
        STEP_PID=
    fi
    exit "$code"
}
trap cleanup EXIT
trap 'stop_on_signal 129' HUP
trap 'stop_on_signal 130' INT
trap 'stop_on_signal 143' TERM

for command in git python3 docker make sed; do
    command -v "$command" >/dev/null 2>&1 || preflight_die "필수 명령을 찾지 못했습니다: $command"
done
python3 - <<'PY' || preflight_die 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
[ -e "$ROOT/.guide" ] || [ -L "$ROOT/.guide" ] || preflight_die '먼저 ./prepare.sh를 실행하십시오.'
python3 "$ROOT/scripts/prepare_marker.py" check-final --root "$ROOT" --guide-id "$GUIDE_ID" \
    || preflight_die 'prepare marker의 directory 또는 leaf 경로가 안전하지 않습니다.'
[ -f "$STATE_FILE" ] || preflight_die '먼저 ./prepare.sh를 실행하십시오.'

state_error=$(python3 - "$STATE_FILE" <<'PY'
import json
import sys
try:
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as error:
    print(error)
    raise SystemExit(1)
required = {
    "guide_id", "head_commit", "source_fingerprint", "index_fingerprint",
    "python_version", "docker_version", "git_version", "make_version", "base_image",
    "debian_snapshot", "recipe", "verifier_image", "verifier_image_id",
}
missing = sorted(key for key in required if not isinstance(payload.get(key), str) or not payload[key])
if payload.get("schema_version") != 1 or payload.get("guide_id") != "computer-networks" or missing or not isinstance(payload.get("package_versions"), dict):
    print("invalid schema, guide ID, or fields: " + ", ".join(missing))
    raise SystemExit(1)
PY
) || preflight_die "prepare marker가 손상되었습니다: $state_error"

read_state()
{
    python3 - "$STATE_FILE" "$1" <<'PY'
import json
import sys
value = json.load(open(sys.argv[1], encoding="utf-8")).get(sys.argv[2])
if not isinstance(value, (str, int)):
    raise SystemExit(1)
print(value)
PY
}

[ "$(read_state head_commit)" = "$(git -C "$ROOT" rev-parse HEAD)" ] || preflight_die 'HEAD가 prepare 이후 바뀌었습니다.'
SOURCE_BEFORE=$(python3 "$ROOT/scripts/repository_state.py" fingerprint --root "$ROOT") || preflight_die 'source fingerprint를 계산하지 못했습니다.'
INDEX_BEFORE=$(python3 "$ROOT/scripts/repository_state.py" index-fingerprint --root "$ROOT") || preflight_die 'index fingerprint를 계산하지 못했습니다.'
[ "$SOURCE_BEFORE" = "$(read_state source_fingerprint)" ] || preflight_die 'source가 prepare 이후 바뀌었습니다.'
[ "$INDEX_BEFORE" = "$(read_state index_fingerprint)" ] || preflight_die 'Git index가 prepare 이후 바뀌었습니다.'
[ "$(read_state python_version)" = "$(python3 -c 'import platform; print(platform.python_version())')" ] || preflight_die 'Python 버전이 prepare 이후 바뀌었습니다.'
[ "$(read_state git_version)" = "$(git --version)" ] || preflight_die 'Git 버전이 prepare 이후 바뀌었습니다.'
[ "$(read_state make_version)" = "$(make --version | sed -n '1p')" ] || preflight_die 'make 버전이 prepare 이후 바뀌었습니다.'

docker info >/dev/null 2>&1 || preflight_die 'Docker daemon에 연결할 수 없습니다.'
[ "$(read_state docker_version)" = "$(docker version --format '{{.Server.Version}}')" ] || preflight_die 'Docker daemon 버전이 prepare 이후 바뀌었습니다.'
BASE_IMAGE='python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2'
[ "$(read_state base_image)" = "$BASE_IMAGE" ] || preflight_die 'prepare marker의 base image digest가 다릅니다.'
VERIFIER_IMAGE_ID=$(read_state verifier_image_id) || preflight_die '검증 이미지 ID를 읽지 못했습니다.'
docker image inspect "$VERIFIER_IMAGE_ID" >/dev/null 2>&1 || preflight_die 'prepare에서 만든 검증 이미지가 없습니다.'
python3 "$ROOT/scripts/prepare_network_image.py" --check-state "$STATE_FILE" || preflight_die '고정 verifier image의 digest·snapshot·package attestation이 실패했습니다.'

RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/guide-computer-networks-verify.XXXXXX") || preflight_die '검증 임시 디렉터리를 만들 수 없습니다.'
WORK_TREE="$RUN_DIR/repository"
python3 "$ROOT/scripts/run_with_timeout.py" 60 -- \
    python3 "$ROOT/scripts/repository_state.py" copy --root "$ROOT" --destination "$WORK_TREE" &
STEP_PID=$!
wait "$STEP_PID" || preflight_die '격리 검증 복사본을 만들지 못했습니다.'
STEP_PID=
mkdir -p "$WORK_TREE/.guide/$GUIDE_ID"
cp "$STATE_FILE" "$WORK_TREE/.guide/$GUIDE_ID/prepared.json"

run_step()
{
    label=$1
    seconds=$2
    shift 2
    output="$RUN_DIR/step-output"
    emit ''
    emit "==> $label"
    python3 "$WORK_TREE/scripts/run_with_timeout.py" "$seconds" -- "$@" >"$output" 2>&1 &
    STEP_PID=$!
    if wait "$STEP_PID"; then
        STEP_PID=
        cat "$output" | tee -a "$VERIFY_LOG"
        PASS_COUNT=$((PASS_COUNT + 1))
        emit "PASS  $label"
    else
        status=$?
        STEP_PID=
        cat "$output" | tee -a "$VERIFY_LOG" >&2
        FAIL_COUNT=$((FAIL_COUNT + 1))
        emit "FAIL  $label (exit=$status)"
    fi
}

cd "$WORK_TREE" || preflight_die '격리 검증 복사본에 들어갈 수 없습니다.'
run_step '저장소 구조·문서·학습 계약' 60 python3 scripts/validate.py
run_step 'validator mutant suite' 120 python3 scripts/test_validator.py
run_step 'workspace 경로·symlink·중단 안전성' 120 python3 scripts/test_workspace_tools.py
run_step 'VERIFY_LOG 상대·저장소·symlink 안전성' 60 python3 scripts/test_verify_log_safety.py
run_step 'owned process-group signal/timeout cleanup' 30 python3 scripts/test-runner-safety.py
run_step 'prepare marker 경로·identity·중단 안전성' 120 python3 scripts/test_prepare_marker_safety.py
run_step 'Python·Shell 정적 검사' 60 make static-check
run_step '기준 구현과 결정적 예제' 180 make reference-check
run_step 'skeleton 예상 실패 계약' 120 make skeleton-check
run_step '알려진 오답·protocol mutant 거부' 180 make test-quality-check

CONTAINER_NAME="guide-cn-$TIMESTAMP-$$"
run_step '고정 Linux privileged 라우팅·NAT·손실 E2E' 240 \
    docker run --rm --pull=never --privileged \
    --name "$CONTAINER_NAME" \
    --label "guide.computer-networks.verify=$RUN_ID" \
    --network none \
    --mount "type=bind,src=$WORK_TREE,dst=/guide,readonly" \
    "$VERIFIER_IMAGE_ID" \
    sh -c 'cp -R /guide /work-guide && cd /work-guide && ./exercises/linux-routing-nat/scripts/preflight.sh all && ./exercises/linux-routing-nat/scripts/run-all.sh'

SOURCE_AFTER=$(python3 "$ROOT/scripts/repository_state.py" fingerprint --root "$ROOT")
INDEX_AFTER=$(python3 "$ROOT/scripts/repository_state.py" index-fingerprint --root "$ROOT")
if [ "$SOURCE_BEFORE" = "$SOURCE_AFTER" ] && [ "$INDEX_BEFORE" = "$INDEX_AFTER" ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
    emit 'PASS  원본 source/index 불변'
else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    emit 'FAIL  verify가 원본 source/index를 변경했습니다.'
fi

remaining=$(docker ps -aq --filter "label=guide.computer-networks.verify=$RUN_ID" 2>/dev/null)
if [ -z "$remaining" ]; then
    PASS_COUNT=$((PASS_COUNT + 1))
    emit 'PASS  Docker run label 자원 정리'
else
    FAIL_COUNT=$((FAIL_COUNT + 1))
    emit "FAIL  Docker run label 자원이 남았습니다: $remaining"
fi

emit 'Verification summary'
emit "passed=$PASS_COUNT failed=$FAIL_COUNT skipped=0"
emit "VERIFY LOG: $VERIFY_LOG"
if [ "$FAIL_COUNT" -eq 0 ]; then
    emit 'RESULT: PASS'
    FINISHED=1
    exit 0
fi
emit 'RESULT: FAIL'
FINISHED=1
exit 1
