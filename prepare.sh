#!/bin/sh
set -eu
GIT_OPTIONAL_LOCKS=0
export GIT_OPTIONAL_LOCKS
PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

GUIDE_ID=computer-networks
ROOT=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
STATE_FILE="$STATE_DIR/prepared.json"
MARKER_TOOL="$ROOT/scripts/prepare_marker.py"
MARKER_CANDIDATE=
STATE_TEMP=
STATE_TEMP_ID=
BEFORE_SOURCE=
BEFORE_INDEX=
SUCCESS=0

fail()
{
    printf 'prepare 실패: %s\n' "$*" >&2
    exit 1
}

finish()
{
    status=$?
    trap - EXIT HUP INT TERM
    if [ -n "${STATE_TEMP:-}" ]; then
        python3 "$MARKER_TOOL" remove \
            --root "$ROOT" --guide-id "$GUIDE_ID" \
            --candidate "$STATE_TEMP" --identity "$STATE_TEMP_ID" \
            >/dev/null 2>&1 || status=1
    fi
    if [ -n "${BEFORE_SOURCE:-}" ]; then
        after_finish_source=$(python3 "$ROOT/scripts/repository_state.py" fingerprint --root "$ROOT") \
            || status=1
        [ "$BEFORE_SOURCE" = "${after_finish_source:-}" ] || {
            printf '%s\n' 'prepare가 source bytes, modes 또는 symlinks를 변경했습니다.' >&2
            status=1
        }
    fi
    if [ -n "${BEFORE_INDEX:-}" ]; then
        after_finish_index=$(python3 "$ROOT/scripts/repository_state.py" index-fingerprint --root "$ROOT") \
            || status=1
        [ "$BEFORE_INDEX" = "${after_finish_index:-}" ] || {
            printf '%s\n' 'prepare가 raw Git index bytes를 변경했습니다.' >&2
            status=1
        }
    fi
    if [ "$status" -ne 0 ] || [ "$SUCCESS" -ne 1 ]; then
        printf 'PREPARE RESULT: FAIL\n' >&2
        [ "$status" -ne 0 ] || status=1
    else
        printf 'PREPARE RESULT: PASS\n'
    fi
    exit "$status"
}
trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

for command in git python3 docker make sed mktemp; do
    command -v "$command" >/dev/null 2>&1 || fail "필수 명령을 찾지 못했습니다: $command"
done
printf 'probe:\n\t@:\n' | make -s -f - probe || fail 'make 실행 probe가 실패했습니다.'

python3 - <<'PY' || fail 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

repository_root=$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null) || fail 'Git 저장소가 아닙니다.'
repository_root=$(CDPATH= cd "$repository_root" && pwd -P)
[ "$repository_root" = "$ROOT" ] || fail '가이드 저장소 최상위 경로에서 실행해야 합니다.'
[ -f "$ROOT/docs/00-roadmap.md" ] || fail '최종 학습 로드맵이 없습니다.'
[ -f "$ROOT/docs/01-link-and-path/01-layers-encapsulation-and-path.md" ] || fail '최종 문서 구조가 아닙니다.'
[ -f "$ROOT/scripts/repository_state.py" ] || fail '저장소 상태 도구가 없습니다.'
[ -f "$MARKER_TOOL" ] || fail 'marker 안전성 도구가 없습니다.'

BEFORE_SOURCE=$(python3 "$ROOT/scripts/repository_state.py" fingerprint --root "$ROOT")
BEFORE_INDEX=$(python3 "$ROOT/scripts/repository_state.py" index-fingerprint --root "$ROOT")

python3 "$MARKER_TOOL" ensure --root "$ROOT" --guide-id "$GUIDE_ID" \
    || fail '.guide와 guide-id 상태 directory를 안전하게 만들 수 없습니다.'
python3 "$MARKER_TOOL" check-final --root "$ROOT" --guide-id "$GUIDE_ID" \
    || fail '기존 final marker가 안전하지 않습니다.'

docker info >/dev/null 2>&1 || fail 'Docker daemon에 연결할 수 없습니다.'
IMAGE_JSON=$(python3 "$ROOT/scripts/prepare_network_image.py" --print-state) \
    || fail '고정 Linux 검증 이미지를 준비하지 못했습니다.'

after_source=$(python3 "$ROOT/scripts/repository_state.py" fingerprint --root "$ROOT")
after_index=$(python3 "$ROOT/scripts/repository_state.py" index-fingerprint --root "$ROOT")
[ "$BEFORE_SOURCE" = "$after_source" ] || fail 'prepare.sh가 source bytes, modes 또는 symlinks를 변경했습니다.'
[ "$BEFORE_INDEX" = "$after_index" ] || fail 'prepare.sh가 Git index를 변경했습니다.'

umask 077
MARKER_CANDIDATE=$(mktemp "$STATE_DIR/.prepared.XXXXXX") \
    || fail '준비 상태 임시 파일을 만들 수 없습니다.'
STATE_TEMP_ID=$(python3 "$MARKER_TOOL" claim \
    --root "$ROOT" --guide-id "$GUIDE_ID" --candidate "$MARKER_CANDIDATE") \
    || fail 'mktemp가 안전한 marker sibling을 만들지 못했습니다.'
STATE_TEMP=$MARKER_CANDIDATE
MARKER_CANDIDATE=

MARKER_JSON=$(GUIDE_ID="$GUIDE_ID" \
HEAD_COMMIT=$(git -C "$ROOT" rev-parse HEAD) \
SOURCE_FINGERPRINT="$after_source" \
INDEX_FINGERPRINT="$after_index" \
PYTHON_VERSION=$(python3 -c 'import platform; print(platform.python_version())') \
DOCKER_VERSION=$(docker version --format '{{.Server.Version}}') \
GIT_VERSION=$(git --version) \
MAKE_VERSION=$(make --version | sed -n '1p') \
python3 - "$IMAGE_JSON" <<'PY'
import json
import os
import sys

image = json.loads(sys.argv[1])
payload = {
    "schema_version": 1,
    "guide_id": os.environ["GUIDE_ID"],
    "head_commit": os.environ["HEAD_COMMIT"],
    "source_fingerprint": os.environ["SOURCE_FINGERPRINT"],
    "index_fingerprint": os.environ["INDEX_FINGERPRINT"],
    "python_version": os.environ["PYTHON_VERSION"],
    "docker_version": os.environ["DOCKER_VERSION"],
    "git_version": os.environ["GIT_VERSION"],
    "make_version": os.environ["MAKE_VERSION"],
    **image,
}
print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
PY
) || fail '준비 상태 JSON을 만들 수 없습니다.'

printf '%s\n' "$MARKER_JSON" | python3 "$MARKER_TOOL" write \
    --root "$ROOT" --guide-id "$GUIDE_ID" \
    --candidate "$STATE_TEMP" --identity "$STATE_TEMP_ID" \
    || fail '검증한 marker 임시 파일에 상태를 쓸 수 없습니다.'
python3 "$MARKER_TOOL" publish \
    --root "$ROOT" --guide-id "$GUIDE_ID" \
    --candidate "$STATE_TEMP" --identity "$STATE_TEMP_ID" \
    || fail '준비 상태 marker를 원자적으로 게시할 수 없습니다.'
STATE_TEMP=
STATE_TEMP_ID=

SUCCESS=1
printf '준비 상태: %s\n' "$STATE_FILE"
printf '다음 명령: ./verify.sh\n'
