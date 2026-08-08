#!/bin/sh
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
VERIFY_DIR="$ROOT/.verify"
VENV_DIR="$VERIFY_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
REQUIREMENTS="$ROOT/scripts/requirements.txt"
MARKER="$VERIFY_DIR/prepared.json"
IMAGE_LIST=""
PROBE_BUILDER=""

section()
{
    printf '\n============================================================\n'
    printf '%s\n' "$1"
    printf '============================================================\n'
}

fail()
{
    printf '[FAIL] %s\n' "$1" >&2
    exit 2
}

require_command()
{
    if ! command -v "$1" >/dev/null 2>&1
    then
        fail "필수 시스템 명령을 찾지 못했습니다: $1. 이 스크립트는 운영체제 패키지를 자동 설치하지 않습니다."
    fi
}

cleanup_probe_builder()
{
    [ -n "$PROBE_BUILDER" ] || return 0
    docker buildx rm -f "$PROBE_BUILDER" >/dev/null 2>&1 || true
    docker rm -f "buildx_buildkit_${PROBE_BUILDER}0" >/dev/null 2>&1 || true
    docker volume rm -f "buildx_buildkit_${PROBE_BUILDER}0_state" >/dev/null 2>&1 || true
}

cleanup()
{
    if [ -n "$PROBE_BUILDER" ]
    then
        cleanup_probe_builder
        PROBE_BUILDER=""
    fi
    if [ -n "$IMAGE_LIST" ]
    then
        rm -f "$IMAGE_LIST"
        IMAGE_LIST=""
    fi
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

section "1. 저장소와 시스템 의존성 확인"

for command in \
    awk cat chmod curl date docker find grep make mkdir mktemp openssl \
    python3 rm sed sh sleep stat tail tar
do
    require_command "$command"
done

[ -f "$ROOT/README.md" ] || fail "저장소 루트에서 실행해 주세요: README.md가 없습니다."
[ -f "$ROOT/docs/00-roadmap.md" ] || fail "docs/00-roadmap.md가 없습니다."
[ -f "$ROOT/scripts/static-verify.py" ] || fail "scripts/static-verify.py가 없습니다."
[ -f "$REQUIREMENTS" ] || fail "scripts/requirements.txt가 없습니다."

if ! python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
    fail "Python 3.10 이상이 필요합니다."
fi

if ! python3 -m venv --help >/dev/null 2>&1
then
    fail "현재 Python에 venv 모듈이 없습니다. Python venv 패키지를 설치한 뒤 다시 실행해 주세요."
fi

if ! docker info >/dev/null 2>&1
then
    fail "Docker daemon을 사용할 수 없습니다. Docker Engine/Desktop을 시작하고 현재 사용자의 접근 권한을 확인해 주세요."
fi

if ! docker compose version >/dev/null 2>&1
then
    fail "Docker Compose v2 plugin을 사용할 수 없습니다."
fi

if ! docker buildx version >/dev/null 2>&1
then
    fail "Docker Buildx plugin을 사용할 수 없습니다. 검증은 전용 builder를 사용해 build cache를 격리합니다."
fi

printf '[PASS] 시스템 의존성\n'

section "2. 구형 상태와 이전 검증 부산물 정리"

# 이전 최종화 과정에서 사용했던 정확한 파일명만 제거합니다. 학습자 소스나
# 임의의 디렉터리를 wildcard로 삭제하지 않습니다.
rm -f \
    "$ROOT/make-out.txt" \
    "$ROOT/tree.txt" \
    "$ROOT/prepare-verify.sh" \
    "$ROOT/before-verify.sh"
rm -rf "$VERIFY_DIR/tmp"

if ! make -C "$ROOT" clean
then
    fail "기존 검증 부산물을 정리하지 못했습니다."
fi

chmod u+x "$ROOT/prepare.sh" "$ROOT/verify.sh"
find "$ROOT/scripts" "$ROOT/exercises" \
    -type f -name '*.sh' -exec chmod u+x {} +

printf '[PASS] 안전한 사전 정리와 실행 권한\n'

section "3. 검증 전용 Python 환경 준비"

mkdir -p "$VERIFY_DIR"
requirements_hash=$(python3 - "$REQUIREMENTS" <<'PY'
from __future__ import annotations
import hashlib
import sys
from pathlib import Path
path = Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest())
PY
)

recreate_venv=0
if [ ! -x "$VENV_PYTHON" ]
then
    recreate_venv=1
elif [ ! -f "$MARKER" ]
then
    recreate_venv=1
else
    prepared_hash=$(
        "$VENV_PYTHON" - "$MARKER" <<'PY' 2>/dev/null || true
from __future__ import annotations
import json
import sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["requirements_sha256"])
except (OSError, KeyError, TypeError, ValueError):
    pass
PY
    )
    [ "$prepared_hash" = "$requirements_hash" ] || recreate_venv=1
fi

if [ "$recreate_venv" -eq 1 ]
then
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR" || fail "검증 전용 Python 환경을 만들지 못했습니다."
fi

"$VENV_PYTHON" -m pip install \
    --disable-pip-version-check \
    --no-input \
    --requirement "$REQUIREMENTS" \
    || fail "Python 검증 의존성을 설치하지 못했습니다. 네트워크와 package index 접근을 확인해 주세요."

"$VENV_PYTHON" - <<'PY'
import yaml
assert yaml.__version__ == "6.0.3", yaml.__version__
PY

printf '[PASS] Python 검증 환경: %s\n' "$VENV_DIR"

# 여기부터 실패하면 Docker 의존성 준비가 끝나지 않은 상태입니다. 이전 marker를
# 제거하고, 모든 준비 단계가 성공한 마지막에만 새 marker를 기록합니다.
rm -f "$MARKER"

section "4. Docker 검증 이미지 준비"

IMAGE_LIST=$(mktemp "${TMPDIR:-/tmp}/guide-web-infra-images.XXXXXX") \
    || fail "임시 image 목록을 만들지 못했습니다."

"$VENV_PYTHON" - "$ROOT" >"$IMAGE_LIST" <<'PY'
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

root = Path(sys.argv[1])
images: set[str] = set()
variable = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:-|-)([^}]*))?\}")


def expand(value: str, defaults: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name, operator, fallback = match.groups()
        current = os.environ.get(name, defaults.get(name, ""))
        if operator == ":-" and not current:
            return fallback or ""
        if operator == "-" and name not in os.environ and name not in defaults:
            return fallback or ""
        return current

    return variable.sub(replace, value)


for dockerfile in sorted(root.rglob("Dockerfile*")):
    if not dockerfile.is_file():
        continue
    defaults: dict[str, str] = {}
    aliases: set[str] = set()
    for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        arg = re.match(r"(?i)^ARG\s+([A-Za-z_][A-Za-z0-9_]*)(?:=([^\s#]+))?", line)
        if arg:
            defaults[arg.group(1)] = arg.group(2) or ""
            continue
        match = re.match(
            r"(?i)^FROM(?:\s+--platform=[^\s]+)?\s+([^\s]+)(?:\s+AS\s+([^\s]+))?",
            line,
        )
        if not match:
            continue
        token = expand(match.group(1), defaults)
        if token and "$" not in token and token.lower() != "scratch" and token.lower() not in aliases:
            images.add(token)
        if match.group(2):
            aliases.add(match.group(2).lower())

for compose_file in sorted(root.glob("exercises/*/*/compose.yaml")):
    try:
        document: Any = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        continue
    if not isinstance(document, dict) or not isinstance(document.get("services"), dict):
        continue
    for service in document["services"].values():
        if not isinstance(service, dict) or "build" in service:
            continue
        image = service.get("image")
        if isinstance(image, str):
            resolved = expand(image, {})
            if resolved and "$" not in resolved:
                images.add(resolved)

for image in sorted(images):
    print(image)
PY

preparation_hash=$("$VENV_PYTHON" - "$ROOT" <<'PY'
from __future__ import annotations

import hashlib
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
paths = {
    root / "prepare.sh",
    root / "scripts" / "requirements.txt",
    *root.rglob("Dockerfile*"),
    *root.glob("exercises/*/*/compose.yaml"),
}
digest = hashlib.sha256()
for path in sorted((item for item in paths if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
    relative = path.relative_to(root).as_posix().encode("utf-8")
    mode = stat.S_IMODE(path.stat().st_mode)
    digest.update(relative + b"\0" + f"{mode:o}".encode("ascii") + b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")
print(digest.hexdigest())
PY
) || fail "준비 입력 fingerprint를 계산하지 못했습니다."

if [ "${GUIDE_PREPARE_PULL:-1}" = 1 ]
then
    while IFS= read -r image
    do
        [ -n "$image" ] || continue
        printf 'pull: %s\n' "$image"
        docker pull "$image" >/dev/null \
            || fail "Docker image를 준비하지 못했습니다: $image"
    done < "$IMAGE_LIST"
else
    printf 'image pull 생략: GUIDE_PREPARE_PULL=%s\n' "${GUIDE_PREPARE_PULL:-}"
    while IFS= read -r image
    do
        [ -n "$image" ] || continue
        docker image inspect "$image" >/dev/null 2>&1 \
            || fail "pull을 생략했지만 로컬 image가 없습니다: $image"
    done < "$IMAGE_LIST"
fi

# verify.sh가 사용할 전용 Buildx builder를 실제로 부팅할 수 있는지 준비 단계에서
# 확인합니다. 이 probe builder와 전용 cache는 즉시 제거합니다.
PROBE_BUILDER="web-infra-prepare-$(date -u +%Y%m%d%H%M%S)-$$"
docker buildx create \
    --name "$PROBE_BUILDER" \
    --driver docker-container \
    --driver-opt default-load=true >/dev/null \
    || fail "default-load를 지원하는 검증용 Buildx builder를 만들 수 없습니다. Buildx 0.14 이상이 필요합니다."
BUILDX_BUILDER="$PROBE_BUILDER" docker buildx inspect --bootstrap >/dev/null \
    || fail "검증용 Buildx builder를 부팅할 수 없습니다."
if ! docker buildx rm -f "$PROBE_BUILDER" >/dev/null
then
    cleanup_probe_builder
    fail "probe Buildx builder를 제거하지 못했습니다."
fi
docker rm -f "buildx_buildkit_${PROBE_BUILDER}0" >/dev/null 2>&1 || true
docker volume rm -f "buildx_buildkit_${PROBE_BUILDER}0_state" >/dev/null 2>&1 || true
if docker container inspect "buildx_buildkit_${PROBE_BUILDER}0" >/dev/null 2>&1 || \
   docker volume inspect "buildx_buildkit_${PROBE_BUILDER}0_state" >/dev/null 2>&1
then
    fail "probe Buildx builder의 container 또는 cache volume이 남았습니다."
fi
PROBE_BUILDER=""

printf '[PASS] Docker image와 Buildx 실행 환경\n'

section "5. 준비 상태 기록"

"$VENV_PYTHON" - "$MARKER" "$requirements_hash" "$preparation_hash" "$IMAGE_LIST" <<'PY'
from __future__ import annotations
import json
import platform
import sys
from pathlib import Path

marker = Path(sys.argv[1])
images = [line for line in Path(sys.argv[4]).read_text(encoding="utf-8").splitlines() if line]
marker.write_text(
    json.dumps(
        {
            "schema_version": 1,
            "requirements_sha256": sys.argv[2],
            "preparation_sha256": sys.argv[3],
            "python": platform.python_version(),
            "pyyaml": __import__("yaml").__version__,
            "docker_images": images,
        },
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
marker.chmod(0o600)
PY

printf 'PREPARE RESULT: PASS\n'
printf '\n다음 명령을 실행하세요:\n  ./verify.sh\n'
