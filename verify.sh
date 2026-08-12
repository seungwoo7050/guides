#!/bin/sh
set -u

if [ "$#" -ne 0 ]; then
    echo "사용법: ./verify.sh" >&2
    echo "learner 구현은 각 exercise 디렉터리의 ./verify.sh workspace로 검사하세요." >&2
    exit 2
fi

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG=${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-web-infra-verify-${TIMESTAMP}-$$.log}
case "$LOG" in
    /*) ;;
    *)
        printf '[FAIL] VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다: %s\n' "$LOG" >&2
        exit 2
        ;;
esac
LOG_PARENT=${LOG%/*}
[ "$LOG_PARENT" != "$LOG" ] || LOG_PARENT="$ROOT"
[ -d "$LOG_PARENT" ] && [ ! -L "$LOG_PARENT" ] || {
    printf '[FAIL] VERIFY_LOG의 기존 실제 디렉터리를 지정하세요: %s\n' "$LOG_PARENT" >&2
    exit 2
}
LOG_DIRECTORY=$(CDPATH='' cd -- "$LOG_PARENT" && pwd -P) || {
    printf '[FAIL] 로그 디렉터리를 확인할 수 없습니다: %s\n' "$LOG_PARENT" >&2
    exit 2
}
LOG="$LOG_DIRECTORY/${LOG##*/}"
case "$LOG" in
    "$ROOT"|"$ROOT"/*)
        printf '[FAIL] VERIFY_LOG는 저장소 밖의 경로여야 합니다: %s\n' "$LOG" >&2
        exit 2
        ;;
esac
if [ -e "$LOG" ] || [ -L "$LOG" ]; then
    printf '[FAIL] 기존 VERIFY_LOG를 덮어쓰지 않습니다: %s\n' "$LOG" >&2
    exit 2
fi
if ! (set -C; : > "$LOG") 2>/dev/null
then
    printf '[FAIL] 새 검증 로그를 배타적으로 만들 수 없습니다: %s\n' "$LOG" >&2
    exit 2
fi

VERIFY_DIR="$ROOT/.verify"
VENV_PYTHON="$VERIFY_DIR/venv/bin/python"
MARKER="$VERIFY_DIR/prepared.json"
REQUIREMENTS="$ROOT/scripts/requirements.txt"
FAILED=0
CLEANED=0
INTERRUPTED=0
WORKDIR=""
ACTIVE_PID=""
SOURCE_MANIFEST=""
RUN_ID=""
BUILDER=""

section()
{
    {
        printf '\n============================================================\n'
        printf '%s\n' "$1"
        printf '============================================================\n'
    } >> "$LOG"
}

emit()
{
    printf '%s\n' "$1"
    printf '%s\n' "$1" >> "$LOG"
}

record_pass()
{
    emit "[PASS] $1"
}

record_fail()
{
    emit "[FAIL] $1"
    FAILED=1
}

fail_preflight()
{
    record_fail "preflight: $1"
    cleanup
    trap - EXIT HUP INT TERM
    emit "RESULT: FAIL"
    printf 'VERIFY LOG: %s\n' "$LOG"
    exit 2
}

require_command()
{
    command -v "$1" >/dev/null 2>&1 \
        || fail_preflight "required command not found: $1"
}

preflight()
{
    section "PREFLIGHT"

    for command in \
        awk cat chmod cmp curl date diff docker find grep make mkdir mktemp \
        openssl ps rm rmdir sed sh sleep stat tail tar tr
    do
        require_command "$command"
    done

    [ -x "$ROOT/prepare.sh" ] \
        || fail_preflight "prepare.sh가 없거나 실행할 수 없습니다."
    [ -x "$VENV_PYTHON" ] \
        || fail_preflight "검증 Python 환경이 없습니다. 먼저 ./prepare.sh를 실행하세요."
    [ -f "$MARKER" ] \
        || fail_preflight "준비 상태 marker가 없습니다. 먼저 ./prepare.sh를 실행하세요."

    current_hash=$(
        "$VENV_PYTHON" - "$REQUIREMENTS" <<'PY'
from __future__ import annotations
import hashlib
import sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
    ) || fail_preflight "requirements hash를 계산하지 못했습니다."

    prepared_hash=$(
        "$VENV_PYTHON" - "$MARKER" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("schema")
    print(data["requirements_sha256"])
except (OSError, KeyError, TypeError, ValueError):
    raise SystemExit(1)
PY
    ) || fail_preflight "준비 상태 marker가 손상되었습니다. ./prepare.sh를 다시 실행하세요."

    [ "$prepared_hash" = "$current_hash" ] \
        || fail_preflight "검증 의존성 정의가 바뀌었습니다. ./prepare.sh를 다시 실행하세요."

    "$VENV_PYTHON" - <<'PY' >/dev/null 2>&1 \
        || fail_preflight "PyYAML 6.0.3 환경이 아닙니다. ./prepare.sh를 다시 실행하세요."
import yaml
raise SystemExit(0 if yaml.__version__ == "6.0.3" else 1)
PY

    docker info >/dev/null 2>&1 \
        || fail_preflight "Docker daemon을 사용할 수 없습니다."
    docker compose version >/dev/null 2>&1 \
        || fail_preflight "Docker Compose v2를 사용할 수 없습니다."
    docker buildx version >/dev/null 2>&1 \
        || fail_preflight "Docker Buildx를 사용할 수 없습니다."

    current_preparation_hash=$("$VENV_PYTHON" - "$ROOT" <<'PY'
from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
paths = {root / "prepare.sh", root / "scripts" / "requirements.txt"}
for current, directories, files in os.walk(root, topdown=True, followlinks=False):
    directories[:] = [
        name
        for name in directories
        if name not in {".git", ".verify", "__pycache__", "workspace", ".workspace.lock"}
        and not name.startswith(".workspace.tmp.")
    ]
    for name in files:
        if name.startswith("Dockerfile") or name == "compose.yaml":
            paths.add(Path(current) / name)
digest = hashlib.sha256()
for path in sorted((item for item in paths if item.is_file()), key=lambda item: item.relative_to(root).as_posix()):
    relative = path.relative_to(root).as_posix().encode("utf-8")
    mode = stat.S_IMODE(path.stat().st_mode)
    digest.update(relative + b"\0" + f"{mode:o}".encode("ascii") + b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")
print(digest.hexdigest())
PY
    ) || fail_preflight "준비 입력 fingerprint를 계산하지 못했습니다."

    marker_values=$("$VENV_PYTHON" - "$MARKER" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path
try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(data["preparation_sha256"])
    for image in data.get("docker_images", []):
        print(image)
except (OSError, KeyError, TypeError, ValueError):
    raise SystemExit(1)
PY
    ) || fail_preflight "준비 상태 marker에 fingerprint 또는 image 목록이 없습니다. ./prepare.sh를 다시 실행하세요."
    prepared_preparation_hash=$(printf '%s\n' "$marker_values" | sed -n '1p')
    [ "$prepared_preparation_hash" = "$current_preparation_hash" ] \
        || fail_preflight "Dockerfile, Compose 또는 준비 계약이 바뀌었습니다. ./prepare.sh를 다시 실행하세요."
    prepared_images=$(printf '%s\n' "$marker_values" | sed '1d')
    for image in $prepared_images
    do
        docker image inspect "$image" >/dev/null 2>&1 \
            || fail_preflight "준비된 Docker image가 없습니다: $image. ./prepare.sh를 다시 실행하세요."
    done

    RUN_ID="$(date -u +%Y%m%d%H%M%S)-$$"
    BUILDER="web-infra-$RUN_ID-builder"
    record_pass "preflight"
}

write_source_manifest()
{
    destination=$1
    "$VENV_PYTHON" - "$ROOT" "$LOG" "$destination" <<'PY'
from __future__ import annotations

import hashlib
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
log = Path(sys.argv[2]).resolve()
destination = Path(sys.argv[3])
ignored_parts = {".git", ".verify", "__pycache__", "workspace", ".workspace.lock"}
ignored_names = {"make-out.txt", "tree.txt"}
records: list[str] = []

paths: list[Path] = []
for current, directories, files in os.walk(root, topdown=True, followlinks=False):
    current_path = Path(current)
    kept: list[str] = []
    for name in directories:
        path = current_path / name
        if name in ignored_parts or name.startswith(".workspace.tmp."):
            continue
        paths.append(path)
        if not path.is_symlink():
            kept.append(name)
    directories[:] = kept
    for name in files:
        path = current_path / name
        if name in ignored_parts or name.startswith(".workspace.tmp."):
            continue
        paths.append(path)

for path in sorted(paths):
    relative = path.relative_to(root)
    if len(relative.parts) == 1 and relative.name in ignored_names:
        continue
    if path.resolve() == log:
        continue
    mode = stat.S_IMODE(path.lstat().st_mode)
    if path.is_symlink():
        records.append(f"L {mode:o} {relative.as_posix()} {os.readlink(path)}")
    elif path.is_file():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append(f"F {mode:o} {relative.as_posix()} {digest}")
    elif path.is_dir():
        records.append(f"D {mode:o} {relative.as_posix()}")

destination.write_text("\n".join(records) + "\n", encoding="utf-8")
PY
}

record_source_manifest()
{
    SOURCE_MANIFEST=$(mktemp "${TMPDIR:-/tmp}/guide-web-infra-source.XXXXXX") \
        || fail_preflight "failed to create source manifest"
    write_source_manifest "$SOURCE_MANIFEST" \
        || fail_preflight "failed to record source manifest"
    record_pass "source tree baseline"
}

check_source_unchanged()
{
    [ -n "$SOURCE_MANIFEST" ] && [ -f "$SOURCE_MANIFEST" ] || return 0
    current=$(mktemp "${TMPDIR:-/tmp}/guide-web-infra-source-current.XXXXXX") \
        || return 1
    if ! write_source_manifest "$current"
    then
        rm -f "$current"
        return 1
    fi
    if cmp -s "$SOURCE_MANIFEST" "$current"
    then
        rm -f "$current"
        return 0
    fi
    printf '원본 저장소가 검증 중 변경되었습니다.\n' >> "$LOG"
    diff -u "$SOURCE_MANIFEST" "$current" >> "$LOG" 2>&1 || true
    rm -f "$current"
    return 1
}

child_pids()
{
    parent=$1
    ps -eo pid=,ppid= 2>/dev/null | awk -v parent="$parent" '$2 == parent { print $1 }'
}

terminate_tree()
{
    (
        parent=$1
        for child in $(child_pids "$parent")
        do
            terminate_tree "$child"
        done
        kill -TERM "$parent" >/dev/null 2>&1 || true
    )
}

stop_active_process()
{
    [ -n "$ACTIVE_PID" ] || return 0
    active=$ACTIVE_PID
    terminate_tree "$active"

    attempt=0
    while kill -0 "$active" >/dev/null 2>&1 && [ "$attempt" -lt 50 ]
    do
        attempt=$((attempt + 1))
        sleep 0.1
    done
    if kill -0 "$active" >/dev/null 2>&1
    then
        for child in $(child_pids "$active")
        do
            kill -KILL "$child" >/dev/null 2>&1 || true
        done
        kill -KILL "$active" >/dev/null 2>&1 || true
    fi
    wait "$active" >/dev/null 2>&1 || true
    ACTIVE_PID=""
}

prepare_worktree()
{
    section "ISOLATED WORKTREE"

    WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/guide-web-infra-verify.XXXXXX") \
        || fail_preflight "failed to create temporary worktree"

    log_relative=""
    case "$LOG" in
        "$ROOT"/*) log_relative=${LOG#"$ROOT"/} ;;
    esac

    if (
        cd "$ROOT" || exit 1
        set -- \
            --exclude='./.git' \
            --exclude='./.verify' \
            --exclude='./exercises/*/workspace' \
            --exclude='./exercises/*/.workspace.lock' \
            --exclude='./exercises/*/.workspace.tmp.*' \
            --exclude='./make-out.txt' \
            --exclude='./tree.txt'
        [ -z "$log_relative" ] || set -- "$@" "--exclude=./$log_relative"
        tar "$@" -cf - .
    ) | tar -xf - -C "$WORKDIR" >> "$LOG" 2>&1
    then
        record_pass "isolated worktree"
    else
        status=$?
        record_fail "isolated worktree (exit=$status)"
        exit "$status"
    fi
}

prepare_builder()
{
    section "EPHEMERAL BUILDX BUILDER"

    if docker buildx create \
        --name "$BUILDER" \
        --driver docker-container \
        --driver-opt default-load=true >> "$LOG" 2>&1
    then
        :
    else
        fail_preflight "default-load를 지원하는 전용 Buildx builder를 만들지 못했습니다. Buildx 0.14 이상이 필요합니다."
    fi

    if BUILDX_BUILDER="$BUILDER" docker buildx inspect --bootstrap >> "$LOG" 2>&1
    then
        record_pass "ephemeral builder: $BUILDER"
    else
        fail_preflight "전용 Buildx builder를 부팅하지 못했습니다."
    fi

    export BUILDX_BUILDER="$BUILDER"
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    export GUIDE_VERIFY_RUN_ID="$RUN_ID"
    export PYTHON="$VENV_PYTHON"
}

run()
{
    name=$1
    shift

    {
        printf '\n============================================================\n'
        printf 'CHECK: %s\n' "$name"
        printf 'COMMAND:'
        for argument in "$@"
        do
            printf ' %s' "$argument"
        done
        printf '\n============================================================\n'
    } >> "$LOG"

    (
        cd "$WORKDIR" &&
        "$@"
    ) >> "$LOG" 2>&1 &
    ACTIVE_PID=$!

    if wait "$ACTIVE_PID"
    then
        ACTIVE_PID=""
        record_pass "$name"
    else
        status=$?
        ACTIVE_PID=""
        record_fail "$name (exit=$status)"
    fi
}

cleanup()
{
    [ "$CLEANED" -eq 0 ] || return 0
    CLEANED=1

    section "CLEANUP"

    stop_active_process

    if [ -n "$WORKDIR" ] && [ -d "$WORKDIR" ]
    then
        if make -C "$WORKDIR" clean >> "$LOG" 2>&1
        then
            record_pass "generated files"
        else
            if [ "$INTERRUPTED" -eq 0 ]
            then
                record_fail "generated files cleanup"
            fi
        fi
    fi

    # 정상 완료 시 각 exercise가 자기 Docker 자원을 정리했는지 먼저 검사합니다.
    # 누수가 있으면 실패로 기록한 뒤 안전망 정리를 수행합니다.
    if [ -n "$RUN_ID" ] && [ "$INTERRUPTED" -eq 0 ] && \
       command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
    then
        if "$ROOT/scripts/cleanup-runtime.sh" check "$RUN_ID" >> "$LOG" 2>&1
        then
            record_pass "exercise runtime cleanup"
        else
            record_fail "exercise가 Docker container/network/volume/image를 남겼습니다."
        fi
    fi

    if [ -n "$RUN_ID" ] && command -v docker >/dev/null 2>&1
    then
        "$ROOT/scripts/cleanup-runtime.sh" clean "$RUN_ID" >> "$LOG" 2>&1 || true
    fi

    if [ -n "$RUN_ID" ] && command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1
    then
        if "$ROOT/scripts/cleanup-runtime.sh" assert-clean "$RUN_ID" >> "$LOG" 2>&1
        then
            record_pass "Docker runtime and builder cleanup"
        elif [ "$INTERRUPTED" -eq 0 ]
        then
            record_fail "Docker runtime 또는 Buildx builder cleanup"
        fi
    fi

    if [ -n "$SOURCE_MANIFEST" ] && [ "$INTERRUPTED" -eq 0 ]
    then
        if check_source_unchanged
        then
            record_pass "source tree unchanged"
        else
            record_fail "source tree changed during verification"
        fi
    fi

    if [ -n "$SOURCE_MANIFEST" ]
    then
        rm -f "$SOURCE_MANIFEST"
        SOURCE_MANIFEST=""
    fi

    if [ -n "$WORKDIR" ] && [ -d "$WORKDIR" ]
    then
        if rm -rf "$WORKDIR"
        then
            record_pass "temporary worktree cleanup"
        elif [ "$INTERRUPTED" -eq 0 ]
        then
            record_fail "temporary worktree cleanup"
        fi
    fi
    WORKDIR=""
}

on_signal()
{
    signal=$1
    INTERRUPTED=1
    emit "[INTERRUPTED] signal=$signal"
    printf 'VERIFY LOG: %s\n' "$LOG"
    trap - HUP INT TERM
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

preflight
record_source_manifest
prepare_worktree
prepare_builder

run "static repository contract" \
    make PYTHON="$VENV_PYTHON" static
run "verifier meta-tests" \
    make PYTHON="$VENV_PYTHON" meta
run "learner workspace generator" \
    make PYTHON="$VENV_PYTHON" workspace-check
run "analysis evidence checker" \
    make PYTHON="$VENV_PYTHON" evidence-check
run "foundations 01-07: reference pass and skeleton rejection" \
    make PYTHON="$VENV_PYTHON" verify-foundations
run "production 08-18: reference pass and skeleton rejection" \
    make PYTHON="$VENV_PYTHON" verify-production
run "selected repeatability checks" \
    make PYTHON="$VENV_PYTHON" verify-repeatability

cleanup
trap - EXIT HUP INT TERM

section "RESULT"
if [ "$FAILED" -eq 0 ]
then
    emit "RESULT: PASS"
    printf 'VERIFY LOG: %s\n' "$LOG"
    exit 0
fi

emit "RESULT: FAIL"
printf 'VERIFY LOG: %s\n' "$LOG"
exit 1
