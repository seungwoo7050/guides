#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_OPTIONAL_LOCKS=0

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="algorithms"
STATE_ROOT="$ROOT/.guide"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
SOURCE_BEFORE="$(mktemp "${TMPDIR:-/tmp}/guide-algorithms-prepare-before.XXXXXX")"
SOURCE_AFTER="$(mktemp "${TMPDIR:-/tmp}/guide-algorithms-prepare-after.XXXXXX")"
INDEX_BEFORE=""
PROBE_DIR=""
MARKER_TEMP=""
MARKER_CANDIDATE=""
SUCCESS=0

log() { printf '[prepare] %s\n' "$*"; }
die() { printf '[prepare] ERROR: %s\n' "$*" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || die "필수 명령이 없습니다: $1"; }

ensure_state_directory() {
  [[ ! -L "$STATE_ROOT" ]] || die '.guide 상태 루트에 symbolic link를 사용할 수 없습니다.'
  if [[ ! -e "$STATE_ROOT" ]]; then
    mkdir -- "$STATE_ROOT" || die '.guide 상태 루트를 만들 수 없습니다.'
  fi
  [[ -d "$STATE_ROOT" && ! -L "$STATE_ROOT" ]] || die '.guide 상태 루트는 실제 directory여야 합니다.'
  [[ ! -L "$STATE_DIR" ]] || die '가이드 상태 경로에 symbolic link를 사용할 수 없습니다.'
  if [[ ! -e "$STATE_DIR" ]]; then
    mkdir -- "$STATE_DIR" || die '가이드 상태 directory를 만들 수 없습니다.'
  fi
  [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || die '가이드 상태 경로는 실제 directory여야 합니다.'
}

cleanup_marker_candidate() {
  [[ -n "$MARKER_CANDIDATE" ]] || return 0
  python3 - "$ROOT" "$GUIDE_ID" "$MARKER_CANDIDATE" <<'PY' >/dev/null 2>&1 || true
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
guide_id = sys.argv[2]
candidate = Path(sys.argv[3])
if candidate.parent != root / ".guide" / guide_id or candidate.name in {"", ".", "..", "prepared.json"}:
    raise SystemExit(0)
flags = os.O_RDONLY
if hasattr(os, "O_DIRECTORY"):
    flags |= os.O_DIRECTORY
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
descriptors = []
try:
    root_fd = os.open(root, flags)
    descriptors.append(root_fd)
    state_fd = os.open(".guide", flags, dir_fd=root_fd)
    descriptors.append(state_fd)
    guide_fd = os.open(guide_id, flags, dir_fd=state_fd)
    descriptors.append(guide_fd)
    metadata = os.stat(candidate.name, dir_fd=guide_fd, follow_symlinks=False)
    if (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 1
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
    ):
        os.unlink(candidate.name, dir_fd=guide_fd)
        os.fsync(guide_fd)
except OSError:
    pass
finally:
    for descriptor in reversed(descriptors):
        os.close(descriptor)
PY
}

index_fingerprint() {
  local index_path
  index_path="$(git_index_path)"
  python3 - "$index_path" <<'PY'
import hashlib
from pathlib import Path
import sys

path = Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
}

git_index_path() {
  local index_path
  index_path="$(git -C "$ROOT" rev-parse --git-path index)"
  [[ "$index_path" == /* ]] || index_path="$ROOT/$index_path"
  printf '%s\n' "$index_path"
}

finish() {
  local status=$?
  trap - EXIT HUP INT TERM
  if [[ -x "$STATE_TOOL" ]]; then
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 || status=1
    if ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      printf '[prepare] ERROR: prepare가 source 파일·mode·symlink를 변경했습니다.\n' >&2
      status=1
    fi
  fi
  if [[ -n "$INDEX_BEFORE" && "$INDEX_BEFORE" != "$(index_fingerprint)" ]]; then
    printf '[prepare] ERROR: prepare가 Git index를 변경했습니다.\n' >&2
    status=1
  fi
  rm -f -- "$SOURCE_BEFORE" "$SOURCE_AFTER"
  [[ -z "$PROBE_DIR" || ! -d "$PROBE_DIR" ]] || rm -rf -- "$PROBE_DIR"
  cleanup_marker_candidate
  [[ -z "$MARKER_TEMP" ]] || rm -f -- "$MARKER_TEMP"
  if (( status != 0 || SUCCESS != 1 )); then
    printf 'PREPARE RESULT: FAIL\n' >&2
    (( status == 0 )) && status=1
    exit "$status"
  fi
  printf 'PREPARE RESULT: PASS\n'
}

main() {
  [[ $# -eq 0 ]] || die '사용법: ./prepare.sh'
  trap finish EXIT
  trap 'exit 129' HUP
  trap 'exit 130' INT
  trap 'exit 143' TERM

  for command_name in git python3 make rsync sh bash find cmp mktemp sed; do
    require_command "$command_name"
  done
  git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die 'Git checkout이 필요합니다.'
  [[ "$(cd -- "$(git -C "$ROOT" rev-parse --show-toplevel)" && pwd -P)" == "$ROOT" ]] \
    || die '저장소 루트에서 실행하십시오.'
  [[ -x "$STATE_TOOL" ]] || die 'repository state 도구가 없거나 실행할 수 없습니다.'
  python3 - <<'PY' || die 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
  ensure_state_directory

  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  local source_fingerprint head_commit
  source_fingerprint="$("$STATE_TOOL" fingerprint --root "$ROOT")"
  INDEX_BEFORE="$(index_fingerprint)"
  head_commit="$(git -C "$ROOT" rev-parse HEAD)"

  PROBE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-algorithms-tool-probe.XXXXXX")"
  mkdir -p -- "$PROBE_DIR/source" "$PROBE_DIR/destination"
  printf 'rsync functional probe\n' >"$PROBE_DIR/source/value.txt"
  chmod 640 "$PROBE_DIR/source/value.txt"
  ln -s value.txt "$PROBE_DIR/source/value-link"
  rsync -a "$PROBE_DIR/source/" "$PROBE_DIR/destination/"
  python3 - "$PROBE_DIR/destination" <<'PY'
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
value = root / "value.txt"
link = root / "value-link"
if value.read_bytes() != b"rsync functional probe\n":
    raise SystemExit("rsync bytes probe 실패")
if stat.S_IMODE(value.stat().st_mode) != 0o640:
    raise SystemExit("rsync mode probe 실패")
if not link.is_symlink() or os.readlink(link) != "value.txt":
    raise SystemExit("rsync symlink probe 실패")
PY
  printf 'all:\n\t@printf "make functional probe\\n"\n' >"$PROBE_DIR/Makefile"
  make -s -C "$PROBE_DIR" all >/dev/null
  [[ -n "$(find "$PROBE_DIR/destination" -type f -name value.txt -print -quit)" ]] \
    || die 'find 기능 probe가 실패했습니다.'
  sh -c 'set -eu; test -f "$1/value.txt"' _ "$PROBE_DIR/destination"
  bash -c 'set -Eeuo pipefail; [[ -L "$1/value-link" ]]' _ "$PROBE_DIR/destination"

  python3 "$ROOT/scripts/validate.py"
  umask 077
  MARKER_CANDIDATE="$(mktemp "$STATE_DIR/.prepared.XXXXXX")" || die 'marker 임시 파일을 만들 수 없습니다.'
  python3 - "$STATE_DIR" "$MARKER_CANDIDATE" <<'PY' || die 'mktemp가 안전한 marker sibling을 만들지 못했습니다.'
import os
from pathlib import Path
import stat
import sys

expected_parent = Path(sys.argv[1])
candidate = Path(sys.argv[2])
if candidate.parent != expected_parent or candidate.name in {"", ".", "..", "prepared.json"}:
    raise SystemExit("marker candidate가 expected state directory의 sibling이 아닙니다")
metadata = candidate.lstat()
if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
    raise SystemExit("marker candidate는 link가 없는 regular file이어야 합니다")
if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
    raise SystemExit("marker candidate의 owner 또는 mode가 안전하지 않습니다")
PY
  MARKER_TEMP="$MARKER_CANDIDATE"
  MARKER_CANDIDATE=""
  GUIDE_MARKER="$MARKER_TEMP" \
  GUIDE_ID_VALUE="$GUIDE_ID" \
  GUIDE_HEAD="$head_commit" \
  GUIDE_SOURCE="$source_fingerprint" \
  GUIDE_INDEX="$INDEX_BEFORE" \
  GUIDE_GIT_VERSION="$(git --version)" \
  GUIDE_MAKE_VERSION="$(make --version | sed -n '1p')" \
  GUIDE_RSYNC_VERSION="$(rsync --version | sed -n '1p')" \
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
    "git_version": os.environ["GUIDE_GIT_VERSION"],
    "make_version": os.environ["GUIDE_MAKE_VERSION"],
    "rsync_version": os.environ["GUIDE_RSYNC_VERSION"],
    "python_version": platform.python_version(),
}
data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
flags = os.O_WRONLY | os.O_TRUNC
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
descriptor = os.open(os.environ["GUIDE_MARKER"], flags)
try:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RuntimeError("marker 임시 파일은 link가 없는 regular file이어야 합니다")
    os.fchmod(descriptor, 0o600)
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view):]
    os.fsync(descriptor)
finally:
    os.close(descriptor)
PY
  python3 - "$ROOT" "$GUIDE_ID" "$MARKER_TEMP" <<'PY'
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
guide_id = sys.argv[2]
temporary = Path(sys.argv[3])
if temporary.parent != root / ".guide" / guide_id or temporary.name == "prepared.json":
    raise SystemExit("marker 임시 경로가 안전한 sibling이 아닙니다")
directory_flags = os.O_RDONLY
if hasattr(os, "O_DIRECTORY"):
    directory_flags |= os.O_DIRECTORY
if hasattr(os, "O_NOFOLLOW"):
    directory_flags |= os.O_NOFOLLOW
root_fd = os.open(root, directory_flags)
state_fd = guide_fd = None
try:
    state_fd = os.open(".guide", directory_flags, dir_fd=root_fd)
    guide_fd = os.open(guide_id, directory_flags, dir_fd=state_fd)
    metadata = os.stat(temporary.name, dir_fd=guide_fd, follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RuntimeError("marker 임시 파일은 link가 없는 regular file이어야 합니다")
    if stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_uid != os.geteuid():
        raise RuntimeError("marker 임시 파일의 mode 또는 owner가 안전하지 않습니다")
    os.replace(
        temporary.name,
        "prepared.json",
        src_dir_fd=guide_fd,
        dst_dir_fd=guide_fd,
    )
    os.fsync(guide_fd)
finally:
    if guide_fd is not None:
        os.close(guide_fd)
    if state_fd is not None:
        os.close(state_fd)
    os.close(root_fd)
PY
  MARKER_TEMP=""
  SUCCESS=1
  log '외부 패키지 없이 검증 환경을 고정했습니다.'
  log '다음 명령: ./verify.sh'
}

main "$@"
