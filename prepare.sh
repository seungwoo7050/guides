#!/usr/bin/env bash
set -Eeuo pipefail

export GIT_OPTIONAL_LOCKS=0

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="operating-systems"
STATE_ROOT="$ROOT/.guide"
STATE_DIR="$STATE_ROOT/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
RUNNER="$ROOT/scripts/run_with_timeout.py"
PUBLISHER="$ROOT/scripts/atomic_directory_publish.py"
SOURCE_BEFORE=""
SOURCE_AFTER=""
INDEX_BEFORE=""
PROBE_DIR=""
MARKER_CANDIDATE=""
MARKER_TEMP=""
MARKER_TEMP_ID=""
SOURCE_CAPTURED=0
SUCCESS=0
FINISHED=0

log() { printf '[prepare] %s\n' "$*"; }
die() { printf '[prepare] ERROR: %s\n' "$*" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || die "필수 명령이 없습니다: $1"; }

index_fingerprint() {
  "$STATE_TOOL" index --root "$ROOT"
}

first_line() {
  python3 -c 'import sys; lines=sys.stdin.read().splitlines(); print(lines[0].strip() if lines else "")'
}

git_version() { git --version; }
make_version() { make --version 2>&1 | first_line; }
rsync_version() { rsync --version 2>&1 | first_line; }
bash_version() { bash --version 2>&1 | first_line; }
cc_version() { cc --version 2>&1 | first_line; }

cleanup_marker_temp() {
  [[ -n "$MARKER_TEMP" ]] || return 0
  python3 - "$ROOT" "$GUIDE_ID" "$MARKER_TEMP" "$MARKER_TEMP_ID" <<'PY'
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
guide_id = sys.argv[2]
candidate = Path(sys.argv[3])
expected = tuple(int(value) for value in sys.argv[4].split(":", 1))
expected_parent = root / ".guide" / guide_id
if candidate.parent != expected_parent or candidate.name == "prepared.json":
    raise SystemExit("marker cleanup 경로가 안전한 sibling이 아닙니다")
if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
    raise SystemExit("marker cleanup에 O_DIRECTORY와 O_NOFOLLOW가 필요합니다")
flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
root_fd = os.open(root, flags)
state_fd = guide_fd = None
try:
    state_fd = os.open(".guide", flags, dir_fd=root_fd)
    guide_fd = os.open(guide_id, flags, dir_fd=state_fd)
    metadata = os.stat(candidate.name, dir_fd=guide_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or (metadata.st_dev, metadata.st_ino) != expected
    ):
        raise RuntimeError("owned marker temp identity가 바뀌어 정리를 거부합니다")
    os.unlink(candidate.name, dir_fd=guide_fd)
    os.fsync(guide_fd)
finally:
    if guide_fd is not None:
        os.close(guide_fd)
    if state_fd is not None:
        os.close(state_fd)
    os.close(root_fd)
PY
}

cleanup() {
  local status=0
  [[ -z "$PROBE_DIR" || ! -d "$PROBE_DIR" ]] || rm -rf -- "$PROBE_DIR"
  cleanup_marker_temp || status=1
  [[ -z "$SOURCE_BEFORE" ]] || rm -f -- "$SOURCE_BEFORE"
  [[ -z "$SOURCE_AFTER" ]] || rm -f -- "$SOURCE_AFTER"
  return "$status"
}

finish() {
  local status=$?
  (( FINISHED == 0 )) || exit "$status"
  FINISHED=1
  trap - EXIT
  trap '' HUP INT TERM
  if (( SOURCE_CAPTURED == 1 )) && [[ -x "$STATE_TOOL" ]]; then
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 || status=1
    if ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      printf '[prepare] ERROR: prepare가 source 파일·directory mode·symlink를 변경했습니다.\n' >&2
      status=1
    fi
  fi
  if [[ -n "$INDEX_BEFORE" && -x "$STATE_TOOL" ]]; then
    if [[ "$INDEX_BEFORE" != "$(index_fingerprint)" ]]; then
      printf '[prepare] ERROR: prepare가 raw Git index를 변경했습니다.\n' >&2
      status=1
    fi
  fi
  cleanup || status=1
  if (( status != 0 || SUCCESS != 1 )); then
    printf 'PREPARE RESULT: FAIL\n' >&2
    (( status == 0 )) && status=1
    exit "$status"
  fi
  printf 'PREPARE RESULT: PASS\n'
}

probe_required_features() {
  PROBE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-os-tool-probe.XXXXXX")"
  cp -- "$("$STATE_TOOL" index-path --root "$ROOT")" "$PROBE_DIR/read-only.index"
  python3 - "$PROBE_DIR" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
(root / "probe.c").write_text(
    "#include <stdatomic.h>\n"
    "int main(void) { atomic_int value = 0; "
    "return atomic_fetch_add_explicit(&value, 1, memory_order_relaxed) == 0 ? 0 : 1; }\n",
    encoding="utf-8",
)
(root / "Makefile").write_text(
    "CC ?= cc\n"
    "CFLAGS = -std=c11 -Wall -Wextra -Werror -pedantic\n"
    "all: probe\n"
    "probe: probe.c\n\t$(CC) $(CFLAGS) probe.c -o probe\n"
    "sanitize: probe.c\n\t$(CC) $(CFLAGS) -O1 -g -fno-omit-frame-pointer "
    "-fsanitize=address,undefined probe.c -o probe-sanitize\n",
    encoding="utf-8",
)
(root / "rsync-source").mkdir()
(root / "rsync-source/value.txt").write_text("rsync probe\n", encoding="utf-8")
PY
  "$RUNNER" --timeout 30 -- make -s -C "$PROBE_DIR" all sanitize
  "$RUNNER" --timeout 5 -- "$PROBE_DIR/probe"
  ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 \
    "$RUNNER" --timeout 5 -- "$PROBE_DIR/probe-sanitize"
  mkdir -p -- "$PROBE_DIR/rsync-copy"
  rsync -a "$PROBE_DIR/rsync-source/" "$PROBE_DIR/rsync-copy/"
  cmp "$PROBE_DIR/rsync-source/value.txt" "$PROBE_DIR/rsync-copy/value.txt"
  [[ -n "$(find "$PROBE_DIR/rsync-copy" -type f -name value.txt -print -quit)" ]] \
    || die 'find 기능 probe가 실패했습니다.'
  bash -c 'set -Eeuo pipefail; [[ -n "$BASH_VERSION" ]]'
  sh -c 'set -eu; test 1 -eq 1'

  mkdir -- "$PROBE_DIR/publish-staging"
  printf 'atomic publish probe\n' >"$PROBE_DIR/publish-staging/value.txt"
  python3 "$PUBLISHER" "$PROBE_DIR/publish-staging" "$PROBE_DIR/published"
  [[ -f "$PROBE_DIR/published/value.txt" ]] || die '원자 directory 게시 probe가 실패했습니다.'
  mkdir -- "$PROBE_DIR/publish-race"
  if python3 "$PUBLISHER" "$PROBE_DIR/publish-race" "$PROBE_DIR/published" >/dev/null 2>&1; then
    die 'exclusive directory rename이 기존 destination을 거부하지 않았습니다.'
  fi

  GIT_INDEX_FILE="$PROBE_DIR/read-only.index" git -C "$ROOT" status --porcelain=v2 --untracked-files=all >/dev/null
  GIT_INDEX_FILE="$PROBE_DIR/read-only.index" git -C "$ROOT" diff --check
  GIT_INDEX_FILE="$PROBE_DIR/read-only.index" git -C "$ROOT" diff --cached --check
}

main() {
  trap finish EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM
  [[ $# -eq 0 ]] || die '사용법: ./prepare.sh'

  for command_name in git python3 rsync bash sh find cmp cp mktemp make cc; do
    require_command "$command_name"
  done
  [[ -x "$STATE_TOOL" ]] || die 'repository state 도구가 없거나 실행할 수 없습니다.'
  [[ -x "$RUNNER" ]] || die 'timeout/process-tree runner가 없거나 실행할 수 없습니다.'
  [[ -x "$PUBLISHER" ]] || die 'exclusive directory publisher가 없거나 실행할 수 없습니다.'
  python3 - <<'PY' || die 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

  SOURCE_BEFORE="$(mktemp "${TMPDIR:-/tmp}/guide-os-prepare-before.XXXXXX")"
  SOURCE_AFTER="$(mktemp "${TMPDIR:-/tmp}/guide-os-prepare-after.XXXXXX")"
  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  SOURCE_CAPTURED=1
  INDEX_BEFORE="$(index_fingerprint)" || die 'raw Git index를 읽을 수 없습니다.'
  git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die 'Git checkout이 필요합니다.'
  [[ "$(cd -- "$(git -C "$ROOT" rev-parse --show-toplevel)" && pwd -P)" == "$ROOT" ]] \
    || die '저장소 루트에서 실행하십시오.'

  local source_fingerprint head_commit
  source_fingerprint="$("$STATE_TOOL" fingerprint --root "$ROOT")"
  head_commit="$(git -C "$ROOT" rev-parse HEAD)"
  probe_required_features
  python3 "$ROOT/scripts/validate.py"

  [[ ! -L "$STATE_ROOT" ]] || die '.guide 상태 루트에 symbolic link를 사용할 수 없습니다.'
  if [[ ! -e "$STATE_ROOT" ]]; then
    mkdir -- "$STATE_ROOT" || die '.guide 상태 루트를 만들 수 없습니다.'
  fi
  [[ -d "$STATE_ROOT" && ! -L "$STATE_ROOT" ]] || die '.guide 상태 루트는 실제 directory여야 합니다.'
  [[ ! -L "$STATE_DIR" ]] || die 'guide-id 상태 경로에 symbolic link를 사용할 수 없습니다.'
  if [[ ! -e "$STATE_DIR" ]]; then
    mkdir -- "$STATE_DIR" || die 'guide-id 상태 directory를 만들 수 없습니다.'
  fi
  [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || die 'guide-id 상태 경로는 실제 directory여야 합니다.'
  [[ "$(cd -- "$STATE_ROOT" && pwd -P)" == "$STATE_ROOT" ]] || die '.guide 상태 루트가 저장소 밖을 가리킵니다.'
  [[ "$(cd -- "$STATE_DIR" && pwd -P)" == "$STATE_DIR" ]] || die 'guide-id 상태 경로가 저장소 밖을 가리킵니다.'
  umask 077
  MARKER_CANDIDATE="$(mktemp "$STATE_DIR/.prepared.XXXXXX")" \
    || die 'marker 임시 파일을 만들 수 없습니다.'
  MARKER_TEMP_ID="$(python3 - "$ROOT" "$GUIDE_ID" "$MARKER_CANDIDATE" <<'PY'
import os
from pathlib import Path
import re
import stat
import sys

root = Path(sys.argv[1])
guide_id = sys.argv[2]
candidate = Path(sys.argv[3])
expected_parent = root / ".guide" / guide_id
if not candidate.is_absolute() or candidate.parent != expected_parent:
    raise SystemExit("mktemp 반환 경로가 lexical marker sibling이 아닙니다")
if expected_parent.resolve(strict=True) != expected_parent:
    raise SystemExit("mktemp 반환 경로의 실제 parent가 상태 directory가 아닙니다")
if re.fullmatch(r"\.prepared\.[A-Za-z0-9]{6}", candidate.name) is None:
    raise SystemExit("mktemp 반환 이름이 무작위 marker 형식이 아닙니다")
path_state = candidate.lstat()
if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
    raise SystemExit("marker claim에 O_DIRECTORY와 O_NOFOLLOW가 필요합니다")
flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
root_fd = os.open(root, flags)
state_fd = guide_fd = None
try:
    state_fd = os.open(".guide", flags, dir_fd=root_fd)
    guide_fd = os.open(guide_id, flags, dir_fd=state_fd)
    metadata = os.stat(candidate.name, dir_fd=guide_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or (metadata.st_dev, metadata.st_ino) != (path_state.st_dev, path_state.st_ino)
    ):
        raise RuntimeError("mktemp 반환 파일 type/link/owner/mode/identity가 안전하지 않습니다")
    print(f"{metadata.st_dev}:{metadata.st_ino}")
finally:
    if guide_fd is not None:
        os.close(guide_fd)
    if state_fd is not None:
        os.close(state_fd)
    os.close(root_fd)
PY
)" || die 'mktemp가 안전한 marker sibling을 만들지 못했습니다.'
  MARKER_TEMP="$MARKER_CANDIDATE"
  MARKER_CANDIDATE=""
  GUIDE_MARKER="$MARKER_TEMP" \
  GUIDE_MARKER_ID="$MARKER_TEMP_ID" \
  GUIDE_ID_VALUE="$GUIDE_ID" \
  GUIDE_HEAD="$head_commit" \
  GUIDE_SOURCE="$source_fingerprint" \
  GUIDE_INDEX="$INDEX_BEFORE" \
  GUIDE_GIT_VERSION="$(git_version)" \
  GUIDE_MAKE_VERSION="$(make_version)" \
  GUIDE_RSYNC_VERSION="$(rsync_version)" \
  GUIDE_BASH_VERSION="$(bash_version)" \
  GUIDE_CC_PATH="$(command -v cc)" \
  GUIDE_CC_VERSION="$(cc_version)" \
    python3 - <<'PY'
import json
import os
import platform
import stat

payload = {
    "schema_version": 1,
    "guide_id": os.environ["GUIDE_ID_VALUE"],
    "head_commit": os.environ["GUIDE_HEAD"],
    "source_fingerprint": os.environ["GUIDE_SOURCE"],
    "index_fingerprint": os.environ["GUIDE_INDEX"],
    "python_version": platform.python_version(),
    "git_version": os.environ["GUIDE_GIT_VERSION"],
    "make_version": os.environ["GUIDE_MAKE_VERSION"],
    "rsync_version": os.environ["GUIDE_RSYNC_VERSION"],
    "bash_version": os.environ["GUIDE_BASH_VERSION"],
    "cc_path": os.environ["GUIDE_CC_PATH"],
    "cc_version": os.environ["GUIDE_CC_VERSION"],
    "platform_system": platform.system(),
}
data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
candidate = os.environ["GUIDE_MARKER"]
expected = tuple(int(value) for value in os.environ["GUIDE_MARKER_ID"].split(":", 1))
if not hasattr(os, "O_NOFOLLOW"):
    raise SystemExit("marker write에 O_NOFOLLOW가 필요합니다")
flags = os.O_WRONLY | os.O_NOFOLLOW
descriptor = os.open(candidate, flags)
try:
    path_state = os.lstat(candidate)
    descriptor_state = os.fstat(descriptor)
    if (
        not stat.S_ISREG(descriptor_state.st_mode)
        or descriptor_state.st_nlink != 1
        or (descriptor_state.st_dev, descriptor_state.st_ino) != expected
        or (path_state.st_dev, path_state.st_ino) != expected
    ):
        raise RuntimeError("쓰기 직전 marker temp identity가 바뀌었습니다")
    os.ftruncate(descriptor, 0)
    os.fchmod(descriptor, 0o600)
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view):]
    os.fsync(descriptor)
finally:
    os.close(descriptor)
PY
  python3 - "$ROOT" "$GUIDE_ID" "$MARKER_TEMP" "$MARKER_TEMP_ID" <<'PY'
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
guide_id = sys.argv[2]
temporary = Path(sys.argv[3])
expected = tuple(int(value) for value in sys.argv[4].split(":", 1))
if temporary.parent != root / ".guide" / guide_id or temporary.name == "prepared.json":
    raise SystemExit("marker 임시 파일이 안전한 sibling이 아닙니다")
if not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
    raise SystemExit("marker publish에 O_DIRECTORY와 O_NOFOLLOW가 필요합니다")
flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
root_fd = os.open(root, flags)
state_fd = guide_fd = None
try:
    state_fd = os.open(".guide", flags, dir_fd=root_fd)
    guide_fd = os.open(guide_id, flags, dir_fd=state_fd)
    metadata = os.stat(temporary.name, dir_fd=guide_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or (metadata.st_dev, metadata.st_ino) != expected
    ):
        raise RuntimeError("게시 직전 marker temp identity가 바뀌었습니다")
    os.replace(temporary.name, "prepared.json", src_dir_fd=guide_fd, dst_dir_fd=guide_fd)
    os.fsync(guide_fd)
finally:
    if guide_fd is not None:
        os.close(guide_fd)
    if state_fd is not None:
        os.close(state_fd)
    os.close(root_fd)
PY
  MARKER_TEMP=""
  MARKER_TEMP_ID=""
  SUCCESS=1
  log 'Python 3.12, Git/make/rsync/bash, C11+sanitizers와 exclusive rename 기능을 고정했습니다.'
  log '다음 명령: ./verify.sh'
}

main "$@"
