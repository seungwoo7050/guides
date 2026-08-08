#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
FINAL_WORKSPACE_DIR="$SCRIPT_DIR/workspace"
WORKSPACE_DIR="$FINAL_WORKSPACE_DIR"
REMOTES_DIR="$WORKSPACE_DIR/remotes"
HOOKS_DIR="$FINAL_WORKSPACE_DIR/.empty-hooks"
LOCK_DIR="$SCRIPT_DIR/.workspace.lock"
MODE=create
TARGET=all
TMP_DIR=''
STAGING_DIR=''
LOCK_HELD=0
FINAL_EXISTED=0
FINAL_IDENTITY=''

usage() {
    cat <<'USAGE'
사용법:
  ./setup.sh [sample|team|all]
  ./setup.sh --reset [sample|team|all]

`exercises/workspace/` 아래에 로컬 Git 실습 저장소를 만듭니다.

명령:
  (인자 없음)             전체 환경을 만듭니다.
  sample                  sample-app만 만듭니다.
  team                    team-app 원격 저장소와 복제 세 개만 만듭니다.
  all                     전체 환경을 만듭니다.
  --reset sample          sample-app만 다시 만듭니다.
  --reset team            team-app 원격 저장소와 복제 세 개만 다시 만듭니다.
  --reset all             전체 환경을 다시 만듭니다.
  --reset                 --reset all과 같습니다.
  -h, --help              이 도움말을 표시합니다.

초기화하면 선택한 실습 저장소 안의 커밋, 브랜치, stash, reflog와 미추적
파일이 삭제됩니다. `exercises/workspace/` 밖의 저장소는 변경하지 않습니다.
USAGE
}

case "$#" in
    0)
        ;;
    1)
        case "$1" in
            sample|team|all) TARGET=$1 ;;
            --reset) MODE=reset; TARGET=all ;;
            -h|--help) usage; exit 0 ;;
            *) echo "알 수 없는 옵션입니다: $1" >&2; usage >&2; exit 2 ;;
        esac
        ;;
    2)
        if [[ "$1" != "--reset" ]]; then
            echo "알 수 없는 옵션입니다: $1" >&2
            usage >&2
            exit 2
        fi
        MODE=reset
        case "$2" in
            sample|team|all) TARGET=$2 ;;
            *) echo "알 수 없는 초기화 대상입니다: $2" >&2; usage >&2; exit 2 ;;
        esac
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac

for command_name in git python3; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "PATH에서 필수 명령을 찾지 못했습니다: $command_name" >&2
        exit 1
    fi
done

if [[ -L "$FINAL_WORKSPACE_DIR" ]]; then
    echo "심볼릭 링크인 작업 공간은 사용하지 않습니다: $FINAL_WORKSPACE_DIR" >&2
    exit 1
fi

cleanup() {
    local status=$?
    trap - EXIT HUP INT TERM
    if [[ -n "$TMP_DIR" && -d "$TMP_DIR" ]]; then
        rm -rf -- "$TMP_DIR"
    fi
    if [[ -n "$STAGING_DIR" && -d "$STAGING_DIR" ]]; then
        rm -rf -- "$STAGING_DIR"
    fi
    if (( LOCK_HELD == 1 )); then
        rmdir -- "$LOCK_DIR" 2>/dev/null || true
    fi
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

if ! mkdir -- "$LOCK_DIR" 2>/dev/null; then
    echo '다른 실습 환경 생성 작업이 진행 중이거나 stale lock이 있습니다.' >&2
    exit 1
fi
LOCK_HELD=1

safe_remove() {
    local path=$1

    case "$path" in
        "$WORKSPACE_DIR"|\
        "$WORKSPACE_DIR/sample-app"|\
        "$WORKSPACE_DIR/team-app-dev-a"|\
        "$WORKSPACE_DIR/team-app-dev-b"|\
        "$WORKSPACE_DIR/team-app-maintainer"|\
        "$REMOTES_DIR/sample-app.git"|\
        "$REMOTES_DIR/team-app.git")
            rm -rf -- "$path"
            ;;
        *)
            echo "예상하지 못한 경로는 삭제하지 않습니다: $path" >&2
            exit 1
            ;;
    esac
}

target_exists() {
    case "$1" in
        sample)
            [[ -e "$WORKSPACE_DIR/sample-app" || -e "$REMOTES_DIR/sample-app.git" ]]
            ;;
        team)
            [[ -e "$WORKSPACE_DIR/team-app-dev-a" ||
               -e "$WORKSPACE_DIR/team-app-dev-b" ||
               -e "$WORKSPACE_DIR/team-app-maintainer" ||
               -e "$REMOTES_DIR/team-app.git" ]]
            ;;
        all)
            [[ -e "$WORKSPACE_DIR" ]]
            ;;
    esac
}

if [[ "$MODE" == create ]] && target_exists "$TARGET"; then
    echo "선택한 실습 환경이 이미 있습니다: $TARGET" >&2
    echo "내용을 삭제해도 되는지 확인한 뒤 해당 초기화 명령을 사용하세요:" >&2
    echo "  ./setup.sh --reset $TARGET" >&2
    exit 1
fi

STAGING_DIR=$(mktemp -d "$SCRIPT_DIR/.workspace.tmp.XXXXXX")
if [[ -d "$FINAL_WORKSPACE_DIR" ]]; then
    FINAL_EXISTED=1
    FINAL_IDENTITY="$(python3 - "$FINAL_WORKSPACE_DIR" <<'PY'
import os, sys
metadata = os.lstat(sys.argv[1])
print(f"{metadata.st_dev}:{metadata.st_ino}")
PY
)"
    cp -R "$FINAL_WORKSPACE_DIR/." "$STAGING_DIR/"
fi
WORKSPACE_DIR="$STAGING_DIR"
REMOTES_DIR="$WORKSPACE_DIR/remotes"
HOOKS_DIR="$FINAL_WORKSPACE_DIR/.empty-hooks"

if [[ "$MODE" == reset ]]; then
    case "$TARGET" in
        sample)
            safe_remove "$WORKSPACE_DIR/sample-app"
            safe_remove "$REMOTES_DIR/sample-app.git"
            ;;
        team)
            safe_remove "$WORKSPACE_DIR/team-app-dev-a"
            safe_remove "$WORKSPACE_DIR/team-app-dev-b"
            safe_remove "$WORKSPACE_DIR/team-app-maintainer"
            safe_remove "$REMOTES_DIR/team-app.git"
            ;;
        all)
            safe_remove "$WORKSPACE_DIR"
            mkdir -- "$WORKSPACE_DIR"
            ;;
    esac
fi

mkdir -p "$REMOTES_DIR" "$WORKSPACE_DIR/.empty-hooks"
TMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/git-guide-exercises.XXXXXX")

configure_identity() {
    local repo=$1
    local name=$2
    local email=$3

    git -C "$repo" config user.name "$name"
    git -C "$repo" config user.email "$email"
    git -C "$repo" config commit.gpgSign false
    git -C "$repo" config tag.gpgSign false
    git -C "$repo" config core.autocrlf false
    git -C "$repo" config protocol.file.allow always
    git -C "$repo" config core.hooksPath "$HOOKS_DIR"
}

init_bare_main() {
    local remote=$1

    git -c init.defaultBranch=main init --bare "$remote" >/dev/null
    git -C "$remote" symbolic-ref HEAD refs/heads/main
}

create_sample_app_remote() {
    local remote="$REMOTES_DIR/sample-app.git"
    local seed="$TMP_DIR/sample-app-seed"

    init_bare_main "$remote"
    git -c init.defaultBranch=main init "$seed" >/dev/null
    configure_identity "$seed" "Guide Learner" "guide@example.invalid"

    mkdir -p "$seed/src" "$seed/tests" "$seed/scripts"

    cat > "$seed/src/validate_title.sh" <<'SOURCE'
#!/usr/bin/env sh

is_valid_title()
{
    [ "$#" -eq 1 ] || return 1
    [ -n "$1" ]
}
SOURCE

    cat > "$seed/tests/test_validate_title.sh" <<'TEST'
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/src/validate_title.sh"

if ! is_valid_title "릴리스 노트 작성"; then
    echo "기준 제목을 허용해야 합니다" >&2
    exit 1
fi

if is_valid_title ""; then
    echo "빈 제목을 거부해야 합니다" >&2
    exit 1
fi

printf '%s\n' "기준 검증 통과"
TEST

    cat > "$seed/scripts/test.sh" <<'SCRIPT'
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
"$ROOT/tests/test_validate_title.sh"
SCRIPT

    chmod +x \
        "$seed/src/validate_title.sh" \
        "$seed/tests/test_validate_title.sh" \
        "$seed/scripts/test.sh"

    cat > "$seed/README.md" <<'README'
# 예제 작업 애플리케이션

Git 작업 흐름을 연습하기 위한 작은 작업 관리 애플리케이션입니다.

## 사용법

짧은 제목으로 작업을 만들고 상태를 기록합니다.

## 제목 규칙

현재 예제는 비어 있지 않은 모든 제목을 허용합니다.

## 검증

커밋을 만들기 전에 저장소 검사를 실행합니다.

```sh
./scripts/test.sh
```

## 디렉터리 구성

- `src/`: 애플리케이션 로직
- `tests/`: 실행 가능한 검사
- `scripts/`: 개발 명령

## 의존성

외부 의존썽이 없습니다.
README

    cat > "$seed/.gitignore" <<'IGNORE'
build/
*.tmp
.env.local
.DS_Store
IGNORE

    git -C "$seed" add .
    git -C "$seed" commit -m "chore: 예제 애플리케이션 구성" >/dev/null
    git -C "$seed" remote add origin "$remote"
    git -C "$seed" push -u origin main >/dev/null

    git -c core.autocrlf=false -c protocol.file.allow=always clone "$remote" "$WORKSPACE_DIR/sample-app" >/dev/null
    git -C "$WORKSPACE_DIR/sample-app" remote set-url origin \
        "$FINAL_WORKSPACE_DIR/remotes/sample-app.git"
    configure_identity "$WORKSPACE_DIR/sample-app" \
        "Guide Learner" "guide@example.invalid"
}

create_team_app_remote() {
    local remote="$REMOTES_DIR/team-app.git"
    local seed="$TMP_DIR/team-app-seed"

    init_bare_main "$remote"
    git -c init.defaultBranch=main init "$seed" >/dev/null
    configure_identity "$seed" "Guide Learner" "guide@example.invalid"

    mkdir -p "$seed/config" "$seed/scripts"

    cat > "$seed/config/task-fields.yml" <<'CONFIG'
fields:
  - title
  - status
CONFIG

    cat > "$seed/scripts/check.sh" <<'SCRIPT'
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FILE="$ROOT/config/task-fields.yml"

if grep -Eq '^(<<<<<<<|=======|>>>>>>>)' "$FILE"; then
    echo "충돌 표시를 발견했습니다: $FILE" >&2
    exit 1
fi

for field in title status; do
    if ! grep -qx "  - $field" "$FILE"; then
        echo "필수 필드가 없습니다: $field" >&2
        exit 1
    fi
done

duplicates=$(awk '/^  - / { count[$0]++; if (count[$0] == 2) print $0 }' "$FILE")
if [ -n "$duplicates" ]; then
    echo "중복 필드를 발견했습니다:" >&2
    printf '%s\n' "$duplicates" >&2
    exit 1
fi

printf '%s\n' "협업 애플리케이션 검사 통과"
SCRIPT

    chmod +x "$seed/scripts/check.sh"

    cat > "$seed/README.md" <<'README'
# 협업 작업 애플리케이션

원격 브랜치, Pull Request, merge, rebase와 충돌 해결을 연습하기 위한 작은 공유 저장소입니다.

## 스키마

작업 필드는 `config/task-fields.yml`에 선언합니다.

## 검사

```sh
./scripts/check.sh
```
README

    cat > "$seed/.gitignore" <<'IGNORE'
*.tmp
.DS_Store
IGNORE

    git -C "$seed" add .
    git -C "$seed" commit -m "chore: 협업 애플리케이션 구성" >/dev/null
    git -C "$seed" remote add origin "$remote"
    git -C "$seed" push -u origin main >/dev/null

    git -c core.autocrlf=false -c protocol.file.allow=always clone "$remote" "$WORKSPACE_DIR/team-app-dev-a" >/dev/null
    git -c core.autocrlf=false -c protocol.file.allow=always clone "$remote" "$WORKSPACE_DIR/team-app-dev-b" >/dev/null
    git -c core.autocrlf=false -c protocol.file.allow=always clone "$remote" "$WORKSPACE_DIR/team-app-maintainer" >/dev/null

    git -C "$WORKSPACE_DIR/team-app-dev-a" remote set-url origin \
        "$FINAL_WORKSPACE_DIR/remotes/team-app.git"
    git -C "$WORKSPACE_DIR/team-app-dev-b" remote set-url origin \
        "$FINAL_WORKSPACE_DIR/remotes/team-app.git"
    git -C "$WORKSPACE_DIR/team-app-maintainer" remote set-url origin \
        "$FINAL_WORKSPACE_DIR/remotes/team-app.git"
    configure_identity "$WORKSPACE_DIR/team-app-dev-a" \
        "Guide Learner" "guide@example.invalid"
    configure_identity "$WORKSPACE_DIR/team-app-dev-b" \
        "Guide Learner" "guide@example.invalid"
    configure_identity "$WORKSPACE_DIR/team-app-maintainer" \
        "Guide Learner" "guide@example.invalid"
}

atomic_publish_no_replace() {
    python3 - "$1" "$2" <<'PY'
import ctypes
import os
import sys

source, destination = map(os.fsencode, sys.argv[1:])
libc = ctypes.CDLL(None, use_errno=True)
if sys.platform == "darwin":
    function = libc.renamex_np
    function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    status = function(source, destination, 0x00000004)  # RENAME_EXCL
elif sys.platform.startswith("linux"):
    function = libc.renameat2
    function.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
    ]
    function.restype = ctypes.c_int
    status = function(-100, source, -100, destination, 0x00000001)  # RENAME_NOREPLACE
else:
    raise SystemExit(f"exclusive atomic publish를 지원하지 않는 플랫폼입니다: {sys.platform}")
if status:
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error), os.fsdecode(destination))
PY
}

atomic_exchange() {
    python3 - "$1" "$2" "$3" <<'PY'
import ctypes
import os
import sys

source_path, destination_path, expected_identity = sys.argv[1:]
metadata = os.lstat(destination_path)
identity = f"{metadata.st_dev}:{metadata.st_ino}"
if identity != expected_identity:
    raise SystemExit("publish 직전 workspace destination identity가 바뀌었습니다.")
source, destination = map(os.fsencode, (source_path, destination_path))
libc = ctypes.CDLL(None, use_errno=True)
if sys.platform == "darwin":
    function = libc.renamex_np
    function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    status = function(source, destination, 0x00000002)  # RENAME_SWAP
elif sys.platform.startswith("linux"):
    function = libc.renameat2
    function.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
    ]
    function.restype = ctypes.c_int
    status = function(-100, source, -100, destination, 0x00000002)  # RENAME_EXCHANGE
else:
    raise SystemExit(f"atomic exchange를 지원하지 않는 플랫폼입니다: {sys.platform}")
if status:
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error), destination_path)
PY
}

case "$TARGET" in
    sample)
        create_sample_app_remote
        ;;
    team)
        create_team_app_remote
        ;;
    all)
        create_sample_app_remote
        create_team_app_remote
        ;;
esac

if [[ "${GUIDE_WORKSPACE_TEST_HOLD:-0}" == 1 ]]; then
    ready_file="${GUIDE_WORKSPACE_TEST_READY_FILE:-}"
    release_file="${GUIDE_WORKSPACE_TEST_RELEASE_FILE:-}"
    if [[ -n "$ready_file" ]]; then
        [[ "$ready_file" == /* && ! -e "$ready_file" && ! -L "$ready_file" ]] || {
            echo 'workspace ready fixture는 새 외부 절대 경로여야 합니다.' >&2
            exit 1
        }
        printf 'ready\n' > "$ready_file"
    fi
    if [[ -n "$release_file" ]]; then
        while [[ ! -e "$release_file" ]]; do sleep 0.02; done
    else
        while :; do sleep 1; done
    fi
fi

if (( FINAL_EXISTED == 1 )); then
    atomic_exchange "$STAGING_DIR" "$FINAL_WORKSPACE_DIR" "$FINAL_IDENTITY"
    rm -rf -- "$STAGING_DIR"
else
    atomic_publish_no_replace "$STAGING_DIR" "$FINAL_WORKSPACE_DIR"
fi
STAGING_DIR=''
WORKSPACE_DIR="$FINAL_WORKSPACE_DIR"
REMOTES_DIR="$WORKSPACE_DIR/remotes"
HOOKS_DIR="$WORKSPACE_DIR/.empty-hooks"
rmdir -- "$LOCK_DIR"
LOCK_HELD=0

cat <<EOF_SUMMARY
Git 실습 환경을 만들었습니다($TARGET).
EOF_SUMMARY

if [[ "$TARGET" == sample || "$TARGET" == all ]]; then
    cat <<EOF_SAMPLE

  $WORKSPACE_DIR/sample-app

예제 검사를 실행합니다.

  cd "$WORKSPACE_DIR/sample-app" && ./scripts/test.sh
EOF_SAMPLE
fi

if [[ "$TARGET" == team || "$TARGET" == all ]]; then
    cat <<EOF_TEAM

  $WORKSPACE_DIR/team-app-dev-a
  $WORKSPACE_DIR/team-app-dev-b
  $WORKSPACE_DIR/team-app-maintainer

협업 검사를 실행합니다.

  cd "$WORKSPACE_DIR/team-app-dev-a" && ./scripts/check.sh
EOF_TEAM
fi

cat <<'EOF_RESET'

초기화 명령:

  ./setup.sh --reset sample
  ./setup.sh --reset team
  ./setup.sh --reset all
EOF_RESET
