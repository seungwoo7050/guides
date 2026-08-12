#!/usr/bin/env bash

set -Eeuo pipefail
umask 022

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="$SCRIPT_DIR"
cd "$ROOT"

fail()
{
    printf 'PREPARE ERROR: %s\n' "$*" >&2
    exit 1
}

note()
{
    printf '%s\n' "$*"
}

need_command()
{
    command -v "$1" >/dev/null 2>&1 || {
        printf 'MISSING: %s\n' "$1" >&2
        return 1
    }
}

installation_hint()
{
    case "$(uname -s 2>/dev/null || true)" in
        Darwin)
            cat >&2 <<'EOF'
macOS 예시:
  xcode-select --install
  brew install cmake python ninja
  # macOS 기본 lsof가 없다면: brew install lsof
EOF
            ;;
        Linux)
            cat >&2 <<'EOF'
Debian/Ubuntu 예시:
  sudo apt install build-essential cmake python3 ninja-build
Fedora 예시:
  sudo dnf install gcc-c++ make cmake python3 ninja-build
EOF
            ;;
        *)
            printf 'C++20 compiler, Make, CMake 3.20+, CTest, Python 3.9+를 설치하세요.\n' >&2
            ;;
    esac
}

if [ ! -f README.md ] || [ ! -f Makefile ] || [ ! -d docs ] || [ ! -d exercises ]; then
    fail "guide-cpp 저장소 루트에서 실행해야 합니다: $ROOT"
fi

note '== 1. 시스템 의존성 확인 =='
missing=0
for command_name in bash make cmake ctest python3; do
    if ! need_command "$command_name"; then
        missing=1
    fi
done
if [ "$(uname -s 2>/dev/null || true)" = 'Darwin' ] && ! need_command lsof; then
    missing=1
fi

CXX_COMMAND="${CXX:-c++}"
case "$CXX_COMMAND" in
    *[[:space:]]*)
        fail "CXX에는 옵션이 아닌 단일 compiler 실행 경로만 지정하세요: $CXX_COMMAND"
        ;;
esac
if ! need_command "$CXX_COMMAND"; then
    missing=1
fi

if [ "$missing" -ne 0 ]; then
    installation_hint
    fail '필수 시스템 도구가 없습니다. prepare.sh는 운영체제 패키지를 자동 설치하지 않습니다.'
fi

if ! python3 - <<'PY'
import sys
if sys.version_info < (3, 9):
    raise SystemExit(f"Python 3.9+ required, found {sys.version.split()[0]}")
PY
then
    installation_hint
    fail 'Python 버전이 부족합니다.'
fi

if ! python3 - <<'PY'
import re
import subprocess
text = subprocess.check_output(["cmake", "--version"], text=True).splitlines()[0]
match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
if not match:
    raise SystemExit(f"CMake version parse failed: {text}")
version = tuple(int(part or 0) for part in match.groups())
if version < (3, 20, 0):
    raise SystemExit(f"CMake 3.20+ required, found {version}")
PY
then
    installation_hint
    fail 'CMake 버전이 부족합니다.'
fi

case "$(uname -s)" in
    Linux|Darwin) ;;
    *) fail '전체 C++98 POSIX 트랙 검증은 Linux, macOS 또는 WSL 환경이 필요합니다.' ;;
esac

note '== 2. 최종 디렉터리 구조 준비 =='
python3 - "$ROOT" <<'PY'
from __future__ import annotations

import hashlib
import os
import shutil
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()

moves = [
    ("docs/01-program-and-type-model.md", "docs/02-cpp98-systems/01-program-and-type-model.md"),
    ("docs/02-lifetime-value-and-ownership.md", "docs/02-cpp98-systems/02-lifetime-value-and-ownership.md"),
    ("docs/03-assigning-object-responsibilities.md", "docs/02-cpp98-systems/03-assigning-object-responsibilities.md"),
    ("docs/04-inheritance-and-polymorphism.md", "docs/02-cpp98-systems/04-inheritance-and-polymorphism.md"),
    ("docs/05-errors-validation-and-casts.md", "docs/02-cpp98-systems/05-errors-validation-and-casts.md"),
    ("docs/06-templates-iterators-and-stl.md", "docs/02-cpp98-systems/06-templates-iterators-and-stl.md"),
    ("docs/07-solving-problems-with-stl.md", "docs/02-cpp98-systems/07-solving-problems-with-stl.md"),
    ("docs/08-posix-sockets-and-event-loop.md", "docs/02-cpp98-systems/08-posix-sockets-and-event-loop.md"),
    ("docs/09-object-oriented-http-server.md", "docs/02-cpp98-systems/09-object-oriented-http-server.md"),
    ("exercises/object-model", "exercises/02-cpp98-systems/object-model"),
    ("exercises/generic-programming", "exercises/02-cpp98-systems/generic-programming"),
    ("exercises/networking", "exercises/02-cpp98-systems/networking"),
    ("reference/cpp98-compatibility.md", "docs/90-appendix/03-cpp98-build-and-compatibility.md"),
    ("reference/stl-internals.md", "docs/90-appendix/04-stl-internals.md"),
]


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def manifest(path: Path):
    if path.is_symlink():
        return {".": ("symlink", mode(path), os.readlink(path))}
    if path.is_file():
        return {".": ("file", mode(path), digest(path))}
    if not path.is_dir():
        return {".": ("other", mode(path), "")}

    result = {".": ("dir", mode(path), "")}
    for item in sorted(path.rglob("*"), key=lambda value: value.as_posix()):
        relative = item.relative_to(path).as_posix()
        if item.is_symlink():
            result[relative] = ("symlink", mode(item), os.readlink(item))
        elif item.is_dir():
            result[relative] = ("dir", mode(item), "")
        elif item.is_file():
            result[relative] = ("file", mode(item), digest(item))
        else:
            result[relative] = ("other", mode(item), "")
    return result


def remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


for old_text, new_text in moves:
    old = root / old_text
    new = root / new_text
    old_exists = old.exists() or old.is_symlink()
    new_exists = new.exists() or new.is_symlink()

    if old_exists and not new_exists:
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old), str(new))
        print(f"MOVE: {old_text} -> {new_text}")
    elif old_exists and new_exists:
        if manifest(old) != manifest(new):
            raise SystemExit(
                f"old/new 경로가 서로 다른 내용으로 함께 존재합니다: {old_text} / {new_text}"
            )
        remove(old)
        print(f"REMOVE DUPLICATE: {old_text}")
    elif new_exists:
        print(f"KEEP: {new_text}")
    else:
        raise SystemExit(f"필수 경로가 원본과 목적지 모두에 없습니다: {old_text} / {new_text}")

reference = root / "reference"
if reference.exists() or reference.is_symlink():
    if reference.is_symlink() or not reference.is_dir():
        raise SystemExit("reference/가 예상한 디렉터리가 아닙니다")
    remaining_files = [
        path for path in reference.rglob("*") if path.is_file() or path.is_symlink()
    ]
    if remaining_files:
        rendered = "\n".join(f"- {path.relative_to(root)}" for path in remaining_files)
        raise SystemExit(f"reference/에 예상하지 못한 파일이 남았습니다:\n{rendered}")
    shutil.rmtree(reference)
    print("DELETE EMPTY: reference/")

for obsolete in ("before-verify.sh", "make-out.txt", "tree.txt"):
    path = root / obsolete
    if path.exists() or path.is_symlink():
        remove(path)
        print(f"DELETE: {obsolete}")
PY

chmod +x \
    prepare.sh \
    verify.sh \
    scripts/manage_artifacts.py \
    scripts/new_workspace.py \
    scripts/run_with_timeout.py \
    scripts/validate_annotations.py \
    scripts/validate_docs.py \
    scripts/verify_modern_skeletons.py \
    scripts/selftest_verifiers.py
find exercises/02-cpp98-systems -type f -name '*.sh' -exec chmod +x {} +

note '== 3. 기존 빌드·검증 부산물 정리 =='
if ! make clean >/dev/null 2>&1; then
    note 'WARN: 기존 clean target 일부가 실패했습니다. 안전한 산출물 정리를 계속합니다.' >&2
fi
python3 scripts/manage_artifacts.py clean "$ROOT"
python3 scripts/manage_artifacts.py audit "$ROOT"

note '== 4. compiler 기능 확인 =='
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/guide-cpp-prepare.XXXXXX")"
cleanup_temp()
{
    rm -rf "$TEMP_ROOT"
}
on_signal()
{
    local code=$1
    trap - EXIT HUP INT TERM
    cleanup_temp
    exit "$code"
}
trap cleanup_temp EXIT
trap 'on_signal 129' HUP
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

cat > "$TEMP_ROOT/modern.cpp" <<'CPP'
#include <compare>
#include <filesystem>
#include <ranges>
#include <stop_token>
#include <thread>
#include <vector>
int main()
{
    std::vector<int> values{1, 2, 3};
    auto view = values | std::views::filter([](int value) { return value > 1; });
    std::jthread worker{[](std::stop_token) {}};
    return std::ranges::distance(view) == 2 ? 0 : 1;
}
CPP
"$CXX_COMMAND" -std=c++20 -Wall -Wextra -Wpedantic -pthread \
    "$TEMP_ROOT/modern.cpp" -o "$TEMP_ROOT/modern"
"$TEMP_ROOT/modern"

cat > "$TEMP_ROOT/cpp98.cpp" <<'CPP'
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>
int main()
{
    struct pollfd descriptor;
    descriptor.fd = -1;
    descriptor.events = POLLIN;
    descriptor.revents = 0;
    return descriptor.fd == -1 ? 0 : 1;
}
CPP
"$CXX_COMMAND" -std=c++98 -Wall -Wextra -Werror -pedantic \
    "$TEMP_ROOT/cpp98.cpp" -o "$TEMP_ROOT/cpp98"
"$TEMP_ROOT/cpp98"

if command -v ninja >/dev/null 2>&1; then
    note "Ninja: $(ninja --version)"
else
    note 'INFO: Ninja가 없어 preset 경로는 사용할 수 없지만 verify.sh의 직접 CMake configure는 가능합니다.'
fi

note '== 5. 저장소 관리 의존성 =='
note '외부 C++·Python package 의존성 없음: 자동 설치할 저장소 관리 패키지가 없습니다.'

note '== 6. 준비 상태 확인 =='
python3 scripts/validate_docs.py --mode structure
python3 scripts/manage_artifacts.py audit "$ROOT"

trap - EXIT HUP INT TERM
cleanup_temp
printf '\nPREPARE RESULT: PASS\n'
