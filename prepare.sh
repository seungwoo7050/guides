#!/bin/sh
set -eu

ROOT=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$ROOT"

BASELINE_SHA=${BASELINE_SHA:-}
if [ -z "$BASELINE_SHA" ] && command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    BASELINE_SHA=$(git rev-list --max-parents=0 HEAD | head -n 1 || true)
fi
BASELINE_SHA=${BASELINE_SHA:-078a6dbeff4f11bc4ec277278a53b0216296619c}
PREPARE_ALLOW_BASELINE_MISMATCH=${PREPARE_ALLOW_BASELINE_MISMATCH:-1}
CC_COMMAND=${CC:-cc}
PREPARE_STATE="$ROOT/.guide-prepare.env"
TEMP_DIR=

say()
{
    printf '%s\n' "$*"
}

warn()
{
    printf '경고: %s\n' "$*" >&2
}

die()
{
    printf 'prepare.sh 실패: %s\n' "$*" >&2
    exit 1
}

cleanup()
{
    if [ -n "${TEMP_DIR:-}" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}

on_signal()
{
    code=$1
    name=$2
    warn "$name 신호로 중단되었습니다"
    exit "$code"
}

trap cleanup EXIT
trap 'on_signal 129 HUP' HUP
trap 'on_signal 130 INT' INT
trap 'on_signal 143 TERM' TERM

require_command()
{
    command -v "$1" >/dev/null 2>&1 || die "필수 명령을 찾을 수 없습니다: $1"
}

require_path()
{
    [ -e "$1" ] || die "guide-c 저장소 루트가 아니거나 필수 경로가 없습니다: $1"
}

say '==> 저장소 확인'
for required in \
    README.md \
    Makefile \
    docs/00-roadmap.md \
    docs/01-foundations \
    docs/02-c-language \
    docs/03-unix-programming \
    docs/04-concurrency \
    docs/90-appendix \
    examples \
    exercises \
    scripts/validate_docs.py \
    scripts/validate_repository.py \
    scripts/new-workspace.sh \
    scripts/test-validator.py \
    scripts/test_workspace.py \
    verify.sh
do
    require_path "$required"
done

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if git cat-file -e "$BASELINE_SHA^{commit}" >/dev/null 2>&1; then
        if ! git merge-base --is-ancestor "$BASELINE_SHA" HEAD >/dev/null 2>&1; then
            if [ "${PREPARE_ALLOW_BASELINE_MISMATCH:-0}" != 1 ]; then
                die "현재 HEAD가 기준 커밋 $BASELINE_SHA 계열이 아닙니다"
            fi
            warn '기준 커밋 불일치를 허용하고 계속합니다'
        fi
    else
        warn "로컬 Git 기록에서 기준 커밋을 찾지 못해 ancestry 검사를 생략합니다: $BASELINE_SHA"
    fi
fi

say '==> 필수 도구 확인'
for command_name in \
    "$CC_COMMAND" make ar python3 sh find grep sed awk diff cmp mktemp cp rm chmod mkdir mv tee dirname uname
 do
    require_command "$command_name"
done

python3 - <<'PY' || die 'Python 3.10 이상이 필요합니다'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(1)
PY

say '==> 구형 경로와 생성 파일 제거'
for obsolete in \
    make-out.txt \
    tree.txt \
    reference \
    docs/01-c-program-model.md \
    docs/02-memory-pointers-strings.md \
    docs/03-data-structures-api-design.md \
    docs/04-build-link-test.md \
    docs/05-variadic-format-api.md \
    docs/06-posix-io-streams.md \
    docs/07-process-fd-pipe.md \
    docs/08-signals-events.md \
    docs/09-shell-parser-executor.md \
    docs/10-threads-time.md
 do
    if [ -e "$obsolete" ] || [ -L "$obsolete" ]; then
        rm -rf "$obsolete"
        say "제거: $obsolete"
    fi
done
rm -f verify.log "$PREPARE_STATE"

say '==> 실행 권한 정규화'
chmod +x prepare.sh verify.sh
chmod +x scripts/new-workspace.sh
find examples exercises -type f -name '*.sh' -exec chmod +x {} +

say '==> 이전 빌드 산출물 정리'
make clean >/dev/null || die 'make clean이 실패했습니다'

TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/guide-c-prepare.XXXXXX")

say '==> C99·POSIX 도구 체인 확인'
cat >"$TEMP_DIR/c99-probe.c" <<'C'
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <signal.h>
#include <stdlib.h>
#include <unistd.h>

static void *worker(void *opaque)
{
    (void)opaque;
    return NULL;
}

int main(void)
{
    int ends[2];
    pthread_t thread;
    struct sigaction action;

    action.sa_handler = SIG_IGN;
    action.sa_flags = 0;
    if (sigemptyset(&action.sa_mask) == -1 ||
        sigaction(SIGUSR1, &action, NULL) == -1 ||
        pipe(ends) == -1 ||
        pthread_create(&thread, NULL, worker, NULL) != 0)
    {
        return 1;
    }
    if (pthread_join(thread, NULL) != 0)
    {
        return 1;
    }
    (void)close(ends[0]);
    (void)close(ends[1]);
    return 0;
}
C
if ! "$CC_COMMAND" -std=c99 -D_POSIX_C_SOURCE=200809L \
    -Wall -Wextra -Wpedantic -Werror \
    "$TEMP_DIR/c99-probe.c" -pthread -o "$TEMP_DIR/c99-probe" >/dev/null 2>&1
then
    die "C99와 POSIX pthread 프로그램을 컴파일할 수 없습니다: $CC_COMMAND"
fi
"$TEMP_DIR/c99-probe" || die 'C99·POSIX probe 실행이 실패했습니다'

HAVE_SANITIZERS=0
ASAN_DETECT_LEAKS=0
ASAN_OPTIONS_VALUE=halt_on_error=1:detect_leaks=0
ASAN_PROCESS_OPTIONS_VALUE=halt_on_error=1:detect_leaks=0
UBSAN_OPTIONS_VALUE=halt_on_error=1:print_stacktrace=1

say '==> AddressSanitizer·UndefinedBehaviorSanitizer 확인'
cat >"$TEMP_DIR/sanitizer-probe.c" <<'C'
#include <stdlib.h>

int main(void)
{
    int *value = malloc(sizeof *value);

    if (value == NULL)
    {
        return 1;
    }
    *value = 7;
    free(value);
    return 0;
}
C
if "$CC_COMMAND" -std=c99 -Wall -Wextra -Wpedantic -Werror -g \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    "$TEMP_DIR/sanitizer-probe.c" -fsanitize=address,undefined \
    -o "$TEMP_DIR/sanitizer-probe" >/dev/null 2>&1 && \
    ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 \
    UBSAN_OPTIONS="$UBSAN_OPTIONS_VALUE" \
    "$TEMP_DIR/sanitizer-probe" >/dev/null 2>&1
then
    HAVE_SANITIZERS=1
    if ASAN_OPTIONS=halt_on_error=1:detect_leaks=1 \
        UBSAN_OPTIONS="$UBSAN_OPTIONS_VALUE" \
        "$TEMP_DIR/sanitizer-probe" >/dev/null 2>&1
    then
        ASAN_DETECT_LEAKS=1
        ASAN_OPTIONS_VALUE=halt_on_error=1:detect_leaks=1
    else
        warn '이 환경은 AddressSanitizer leak detection을 안정적으로 실행하지 못해 detect_leaks=0을 사용합니다'
    fi
else
    warn 'AddressSanitizer·UndefinedBehaviorSanitizer를 사용할 수 없어 해당 검사를 skip합니다'
fi

HAVE_TSAN=0
TSAN_OPTIONS_VALUE=halt_on_error=1
say '==> ThreadSanitizer 확인'
cat >"$TEMP_DIR/tsan-probe.c" <<'C'
#include <pthread.h>

static int value;

static void *worker(void *opaque)
{
    (void)opaque;
    value = 1;
    return NULL;
}

int main(void)
{
    pthread_t thread;

    if (pthread_create(&thread, NULL, worker, NULL) != 0)
    {
        return 1;
    }
    if (pthread_join(thread, NULL) != 0)
    {
        return 1;
    }
    return value == 1 ? 0 : 1;
}
C
if "$CC_COMMAND" -std=c99 -Wall -Wextra -Wpedantic -Werror -g \
    -fsanitize=thread -fno-omit-frame-pointer \
    "$TEMP_DIR/tsan-probe.c" -pthread -fsanitize=thread \
    -o "$TEMP_DIR/tsan-probe" >/dev/null 2>&1 && \
    TSAN_OPTIONS="$TSAN_OPTIONS_VALUE" "$TEMP_DIR/tsan-probe" >/dev/null 2>&1
then
    HAVE_TSAN=1
else
    warn 'ThreadSanitizer를 사용할 수 없어 data-race 검사를 skip합니다'
fi

READLINE_CPPFLAGS_INPUT=${READLINE_CPPFLAGS:-}
READLINE_LDFLAGS_INPUT=${READLINE_LDFLAGS:-}
READLINE_LDLIBS_INPUT=${READLINE_LDLIBS:-}
HAVE_READLINE=0
READLINE_CPPFLAGS=
READLINE_LDFLAGS=
READLINE_LDLIBS=-lreadline

cat >"$TEMP_DIR/readline-probe.c" <<'C'
#include <readline/history.h>
#include <readline/readline.h>

int main(void)
{
    char *(*reader)(const char *) = readline;
    HIST_ENTRY *entry;

    (void)reader;
    add_history("probe");
    entry = history_get(history_base);
    return entry != NULL ? 0 : 1;
}
C

try_readline()
{
    candidate_cppflags=$1
    candidate_ldflags=$2
    candidate_ldlibs=$3

    # pkg-config와 컴파일러가 반환한 일반적인 공백 구분 플래그를 사용합니다.
    # 경로에 공백이 있는 비표준 설치는 READLINE_* 환경 변수로 직접 지정할 수 있습니다.
    if "$CC_COMMAND" $candidate_cppflags -std=c99 -Wall -Wextra -Wpedantic -Werror \
        "$TEMP_DIR/readline-probe.c" $candidate_ldflags $candidate_ldlibs \
        -o "$TEMP_DIR/readline-probe" >/dev/null 2>&1 && \
        "$TEMP_DIR/readline-probe" >/dev/null 2>&1
    then
        HAVE_READLINE=1
        READLINE_CPPFLAGS=$candidate_cppflags
        READLINE_LDFLAGS=$candidate_ldflags
        READLINE_LDLIBS=$candidate_ldlibs
        return 0
    fi
    return 1
}

say '==> Readline 선택 기능 확인'
if [ -n "$READLINE_CPPFLAGS_INPUT" ] || \
   [ -n "$READLINE_LDFLAGS_INPUT" ] || \
   [ -n "$READLINE_LDLIBS_INPUT" ]; then
    try_readline \
        "$READLINE_CPPFLAGS_INPUT" \
        "$READLINE_LDFLAGS_INPUT" \
        "${READLINE_LDLIBS_INPUT:--lreadline}" || true
fi

if [ "$HAVE_READLINE" -eq 0 ] && command -v pkg-config >/dev/null 2>&1 && \
   pkg-config --exists readline >/dev/null 2>&1; then
    try_readline \
        "$(pkg-config --cflags readline)" \
        "$(pkg-config --libs-only-L readline)" \
        "$(pkg-config --libs-only-l --libs-only-other readline)" || true
fi

if [ "$HAVE_READLINE" -eq 0 ]; then
    try_readline '' '' '-lreadline' || true
fi

if [ "$HAVE_READLINE" -eq 0 ] && command -v brew >/dev/null 2>&1; then
    readline_prefix=$(brew --prefix readline 2>/dev/null || true)
    if [ -n "$readline_prefix" ]; then
        try_readline \
            "-I$readline_prefix/include" \
            "-L$readline_prefix/lib" \
            '-lreadline' || true
    fi
fi

if [ "$HAVE_READLINE" -eq 0 ]; then
    warn 'Readline 개발 파일을 찾지 못해 선택적 Readline 검사를 skip합니다'
    case $(uname -s 2>/dev/null || printf unknown) in
        Darwin)
            warn '설치 예: brew install readline pkg-config'
            ;;
        Linux)
            warn '설치 예: Debian/Ubuntu는 libreadline-dev, Fedora는 readline-devel'
            ;;
    esac
fi

say '==> 준비 상태 기록'
GUIDE_PREPARED=1 \
GUIDE_BASELINE_SHA="$BASELINE_SHA" \
GUIDE_CC="$CC_COMMAND" \
GUIDE_HAVE_SANITIZERS="$HAVE_SANITIZERS" \
GUIDE_ASAN_DETECT_LEAKS="$ASAN_DETECT_LEAKS" \
GUIDE_ASAN_OPTIONS="$ASAN_OPTIONS_VALUE" \
GUIDE_ASAN_PROCESS_OPTIONS="$ASAN_PROCESS_OPTIONS_VALUE" \
GUIDE_UBSAN_OPTIONS="$UBSAN_OPTIONS_VALUE" \
GUIDE_HAVE_TSAN="$HAVE_TSAN" \
GUIDE_TSAN_OPTIONS="$TSAN_OPTIONS_VALUE" \
GUIDE_HAVE_READLINE="$HAVE_READLINE" \
GUIDE_READLINE_CPPFLAGS="$READLINE_CPPFLAGS" \
GUIDE_READLINE_LDFLAGS="$READLINE_LDFLAGS" \
GUIDE_READLINE_LDLIBS="$READLINE_LDLIBS" \
python3 - "$PREPARE_STATE.tmp" <<'PY'
import os
import shlex
import sys

keys = (
    "GUIDE_PREPARED",
    "GUIDE_BASELINE_SHA",
    "GUIDE_CC",
    "GUIDE_HAVE_SANITIZERS",
    "GUIDE_ASAN_DETECT_LEAKS",
    "GUIDE_ASAN_OPTIONS",
    "GUIDE_ASAN_PROCESS_OPTIONS",
    "GUIDE_UBSAN_OPTIONS",
    "GUIDE_HAVE_TSAN",
    "GUIDE_TSAN_OPTIONS",
    "GUIDE_HAVE_READLINE",
    "GUIDE_READLINE_CPPFLAGS",
    "GUIDE_READLINE_LDFLAGS",
    "GUIDE_READLINE_LDLIBS",
)
with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as stream:
    stream.write("# prepare.sh가 생성한 검증 환경입니다. 직접 수정하지 않습니다.\n")
    for key in keys:
        stream.write(f"{key}={shlex.quote(os.environ[key])}\n")
PY
mv "$PREPARE_STATE.tmp" "$PREPARE_STATE"
chmod 600 "$PREPARE_STATE"

python3 scripts/validate_repository.py --clean

say ''
say 'PREPARE RESULT: PASS'
say "  compiler: $CC_COMMAND"
say "  ASan/UBSan: $HAVE_SANITIZERS (leak detection=$ASAN_DETECT_LEAKS)"
say "  TSan: $HAVE_TSAN"
say "  Readline: $HAVE_READLINE"
say '다음 명령: ./verify.sh'
