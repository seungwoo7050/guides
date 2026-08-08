#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEMPORARY="$(mktemp -d "${TMPDIR:-/tmp}/guide-prepare-safety.XXXXXX")"
REPOSITORY="$TEMPORARY/repository"
HOLD_PID=''
export GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1

die() { printf 'prepare-safety: %s\n' "$*" >&2; exit 1; }
finish() {
    local status=$?
    trap - EXIT HUP INT TERM
    if [[ -n "$HOLD_PID" ]]; then
        kill -TERM "$HOLD_PID" 2>/dev/null || true
        wait "$HOLD_PID" 2>/dev/null || true
    fi
    rm -rf -- "$TEMPORARY"
    exit "$status"
}
trap finish EXIT HUP INT TERM

for command_name in git bash python3 mktemp make; do
    command -v "$command_name" >/dev/null 2>&1 || die "필수 명령 누락: $command_name"
done

python3 - "$ROOT" "$REPOSITORY" <<'PY'
import shutil, sys
from pathlib import Path
source, target = map(Path, sys.argv[1:])
shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns(
    ".git", ".guide", ".venv", ".pytest_cache", "__pycache__", "workspace",
    "*.pyc", "*.pyo", "*.log"))
PY

if [[ -d "$REPOSITORY/exercises/command-checker" ]]; then
    GUIDE_ID=python
elif [[ -d "$REPOSITORY/exercises/system-investigation" ]]; then
    GUIDE_ID=unix-systems
elif [[ -f "$REPOSITORY/exercises/setup.sh" ]]; then
    GUIDE_ID=git
else
    die 'guide id를 식별하지 못했습니다.'
fi

git -C "$REPOSITORY" init -q
git -C "$REPOSITORY" config user.name 'Guide Safety Test'
git -C "$REPOSITORY" config user.email 'guide-safety@example.invalid'
while IFS= read -r relative; do
    [[ -n "$relative" ]] || continue
    git -C "$REPOSITORY" add -- "$relative"
done < "$REPOSITORY/scripts/layout-manifest.txt"
git -C "$REPOSITORY" commit -q -m 'test fixture'

if [[ "$GUIDE_ID" == python ]]; then
    mkdir -p -- "$REPOSITORY/exercises/command-checker/workspace/learner"
    printf '학습자 작업을 보존합니다.\n' > \
        "$REPOSITORY/exercises/command-checker/workspace/learner/sentinel.py"
    chmod 0640 "$REPOSITORY/exercises/command-checker/workspace/learner/sentinel.py"
fi

BASE_SOURCE="$(python3 -B "$REPOSITORY/scripts/repository_state.py" fingerprint --root "$REPOSITORY")"
BASE_LEARNER_SOURCE="$(python3 -B "$REPOSITORY/scripts/repository_state.py" fingerprint \
    --root "$REPOSITORY" --include-workspace)"
RAW_INDEX_PATH="$(git -C "$REPOSITORY" rev-parse --path-format=absolute --git-path index)"
raw_index_hash() {
    python3 - "$RAW_INDEX_PATH" <<'PY'
import hashlib, sys
from pathlib import Path
print(hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}
BASE_RAW_INDEX="$(raw_index_hash)"

STATE_DIR="$REPOSITORY/.guide/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
SENTINEL="$TEMPORARY/sentinel"
printf 'do not follow this sentinel\n' > "$SENTINEL"
chmod 0640 "$SENTINEL"

snapshot() {
    python3 - "$1" <<'PY'
import hashlib, stat, sys
from pathlib import Path
path = Path(sys.argv[1])
metadata = path.stat()
if not stat.S_ISREG(metadata.st_mode):
    raise SystemExit(f"not a regular file: {path}")
print(f"{hashlib.sha256(path.read_bytes()).hexdigest()}:{stat.S_IMODE(metadata.st_mode):04o}:{metadata.st_size}")
PY
}

assert_snapshot() {
    local path=$1 expected=$2 label=$3
    [[ "$(snapshot "$path")" == "$expected" ]] || die "$label bytes/mode가 바뀌었습니다."
}

(cd "$REPOSITORY" && ./prepare.sh > "$TEMPORARY/baseline.log")
[[ -f "$MARKER" && ! -L "$MARKER" ]] || die 'baseline marker가 일반 파일이 아닙니다.'
[[ "$(python3 - "$MARKER" <<'PY'
import stat, sys
print(f"{stat.S_IMODE(__import__('os').stat(sys.argv[1]).st_mode):04o}")
PY
)" == 0600 ]] || die 'marker mode가 0600이 아닙니다.'
MARKER_SNAPSHOT="$(snapshot "$MARKER")"
SENTINEL_SNAPSHOT="$(snapshot "$SENTINEL")"

(
    candidate="$STATE_DIR/prepared.json.tmp.$BASHPID"
    printf '%s\n' "$candidate" > "$TEMPORARY/predictable-path"
    ln -s -- "$SENTINEL" "$candidate"
    cd "$REPOSITORY"
    exec ./prepare.sh
) > "$TEMPORARY/predictable.log"
PREDICTABLE="$(cat "$TEMPORARY/predictable-path")"
[[ -L "$PREDICTABLE" ]] || die '예측 가능한 이전 temp symlink가 예상 밖으로 변경됐습니다.'
assert_snapshot "$SENTINEL" "$SENTINEL_SNAPSHOT" 'predictable temp sentinel'
rm -- "$PREDICTABLE"

FAKE_MKTEMP_DIR="$TEMPORARY/fake-mktemp"
mkdir -- "$FAKE_MKTEMP_DIR"
printf '#!/bin/sh\nprintf "%%s\\n" "$GUIDE_FAKE_TEMP"\n' > "$FAKE_MKTEMP_DIR/mktemp"
chmod 0755 "$FAKE_MKTEMP_DIR/mktemp"
ATTACKER_TEMP="$STATE_DIR/.prepared.attacker"
ln -s -- "$SENTINEL" "$ATTACKER_TEMP"
if (cd "$REPOSITORY" && env GUIDE_FAKE_TEMP="$ATTACKER_TEMP" \
        PATH="$FAKE_MKTEMP_DIR:$PATH" ./prepare.sh > "$TEMPORARY/fake-mktemp.log" 2>&1); then
    die 'symlink를 반환한 mktemp를 허용했습니다.'
fi
assert_snapshot "$SENTINEL" "$SENTINEL_SNAPSHOT" 'mktemp symlink sentinel'
assert_snapshot "$MARKER" "$MARKER_SNAPSHOT" 'mktemp failure marker'
rm -- "$ATTACKER_TEMP"
if (cd "$REPOSITORY" && env GUIDE_FAKE_TEMP="$SENTINEL" \
        PATH="$FAKE_MKTEMP_DIR:$PATH" ./prepare.sh > "$TEMPORARY/fake-mktemp-outside.log" 2>&1); then
    die '저장소 밖 일반 파일을 반환한 mktemp를 허용했습니다.'
fi
assert_snapshot "$SENTINEL" "$SENTINEL_SNAPSHOT" 'mktemp outside regular sentinel'
assert_snapshot "$MARKER" "$MARKER_SNAPSHOT" 'mktemp outside failure marker'
mkdir -- "$STATE_DIR/.prepared.x"
printf 'nested regular sentinel\n' > "$STATE_DIR/.prepared.x/abcd"
chmod 0640 "$STATE_DIR/.prepared.x/abcd"
NESTED_SNAPSHOT="$(snapshot "$STATE_DIR/.prepared.x/abcd")"
if (cd "$REPOSITORY" && env GUIDE_FAKE_TEMP="$STATE_DIR/.prepared.x/abcd" \
        PATH="$FAKE_MKTEMP_DIR:$PATH" ./prepare.sh > "$TEMPORARY/fake-mktemp-nested.log" 2>&1); then
    die 'nested 일반 파일을 반환한 mktemp를 허용했습니다.'
fi
assert_snapshot "$STATE_DIR/.prepared.x/abcd" "$NESTED_SNAPSHOT" 'mktemp nested regular sentinel'
assert_snapshot "$MARKER" "$MARKER_SNAPSHOT" 'mktemp nested failure marker'
rm -rf -- "$STATE_DIR/.prepared.x"

FAKE_MAKE_DIR="$TEMPORARY/fake-make"
mkdir -- "$FAKE_MAKE_DIR"
printf '#!/bin/sh\nif [ "$1" = --version ]; then printf "fake make 1.0\\n"; exit 0; fi\nprintf "WRONG_MAKE_PROBE\\n"\n' > "$FAKE_MAKE_DIR/make"
chmod 0755 "$FAKE_MAKE_DIR/make"
if (cd "$REPOSITORY" && PATH="$FAKE_MAKE_DIR:$PATH" \
        ./prepare.sh > "$TEMPORARY/fake-make.log" 2>&1); then
    die '실행 불가능한 make probe를 허용했습니다.'
fi
assert_snapshot "$MARKER" "$MARKER_SNAPSHOT" 'make probe failure marker'

if [[ "$GUIDE_ID" == unix-systems ]]; then
    FAKE_PS_DIR="$TEMPORARY/fake-ps"
    mkdir -- "$FAKE_PS_DIR"
    printf '#!/bin/sh\nexit 0\n' > "$FAKE_PS_DIR/ps"
    chmod 0755 "$FAKE_PS_DIR/ps"
    if (cd "$REPOSITORY" && PATH="$FAKE_PS_DIR:$PATH" \
            ./prepare.sh > "$TEMPORARY/fake-ps.log" 2>&1); then
        die '빈 ps 기능 probe를 허용했습니다.'
    fi
    assert_snapshot "$MARKER" "$MARKER_SNAPSHOT" 'ps probe failure marker'
fi

mv -- "$MARKER" "$TEMPORARY/marker.saved"
ln -s -- "$SENTINEL" "$MARKER"
if (cd "$REPOSITORY" && ./prepare.sh > "$TEMPORARY/marker-symlink.log" 2>&1); then
    die 'final marker symlink를 허용했습니다.'
fi
[[ -L "$MARKER" ]] || die 'final marker symlink가 실패 경로에서 제거됐습니다.'
assert_snapshot "$SENTINEL" "$SENTINEL_SNAPSHOT" 'final marker symlink sentinel'
rm -- "$MARKER"
mv -- "$TEMPORARY/marker.saved" "$MARKER"

mv -- "$STATE_DIR" "$TEMPORARY/state.saved"
mkdir -- "$TEMPORARY/state-escape"
printf 'state escape sentinel\n' > "$TEMPORARY/state-escape/prepared.json"
chmod 0640 "$TEMPORARY/state-escape/prepared.json"
STATE_ESCAPE_SNAPSHOT="$(snapshot "$TEMPORARY/state-escape/prepared.json")"
ln -s -- "$TEMPORARY/state-escape" "$STATE_DIR"
if (cd "$REPOSITORY" && ./prepare.sh > "$TEMPORARY/state-symlink.log" 2>&1); then
    die 'guide-id directory symlink를 허용했습니다.'
fi
[[ -L "$STATE_DIR" ]] || die 'guide-id directory symlink가 실패 경로에서 제거됐습니다.'
assert_snapshot "$TEMPORARY/state-escape/prepared.json" "$STATE_ESCAPE_SNAPSHOT" 'state directory sentinel'
rm -- "$STATE_DIR"
mv -- "$TEMPORARY/state.saved" "$STATE_DIR"

mv -- "$REPOSITORY/.guide" "$TEMPORARY/guide.saved"
mkdir -p -- "$TEMPORARY/guide-escape/$GUIDE_ID"
printf 'guide escape sentinel\n' > "$TEMPORARY/guide-escape/$GUIDE_ID/prepared.json"
chmod 0640 "$TEMPORARY/guide-escape/$GUIDE_ID/prepared.json"
GUIDE_ESCAPE_SNAPSHOT="$(snapshot "$TEMPORARY/guide-escape/$GUIDE_ID/prepared.json")"
ln -s -- "$TEMPORARY/guide-escape" "$REPOSITORY/.guide"
if (cd "$REPOSITORY" && ./prepare.sh > "$TEMPORARY/guide-symlink.log" 2>&1); then
    die '.guide directory symlink를 허용했습니다.'
fi
[[ -L "$REPOSITORY/.guide" ]] || die '.guide symlink가 실패 경로에서 제거됐습니다.'
assert_snapshot "$TEMPORARY/guide-escape/$GUIDE_ID/prepared.json" "$GUIDE_ESCAPE_SNAPSHOT" '.guide sentinel'
rm -- "$REPOSITORY/.guide"
mv -- "$TEMPORARY/guide.saved" "$REPOSITORY/.guide"

READY="$TEMPORARY/hold.ready"
RELEASE="$TEMPORARY/hold.release"
MARKER_SNAPSHOT="$(snapshot "$MARKER")"
(
    cd "$REPOSITORY"
    exec env GUIDE_PREPARE_TEST_HOLD=1 GUIDE_PREPARE_TEST_READY_FILE="$READY" \
        GUIDE_PREPARE_TEST_RELEASE_FILE="$RELEASE" ./prepare.sh
) > "$TEMPORARY/signal.log" 2>&1 &
HOLD_PID=$!
for _ in {1..500}; do
    [[ -s "$READY" ]] && break
    kill -0 "$HOLD_PID" 2>/dev/null || break
    sleep 0.02
done
[[ -s "$READY" ]] || die 'signal cleanup fixture가 준비되지 않았습니다.'
python3 - "$STATE_DIR" <<'PY'
import stat, sys
from pathlib import Path
paths = list(Path(sys.argv[1]).glob(".prepared.*"))
if len(paths) != 1:
    raise SystemExit(f"expected one owned marker temp, got {paths}")
metadata = paths[0].lstat()
if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
    raise SystemExit(f"unsafe marker temp mode/type: {paths[0]}")
PY
kill -TERM "$HOLD_PID"
if wait "$HOLD_PID"; then
    die '중단된 prepare가 성공했습니다.'
fi
HOLD_PID=''
assert_snapshot "$MARKER" "$MARKER_SNAPSHOT" 'signal failure marker'
[[ -z "$(find "$STATE_DIR" -maxdepth 1 -name '.prepared.*' -print -quit)" ]] || \
    die '중단 뒤 owned marker temp가 남았습니다.'
[[ "$BASE_SOURCE" == "$(python3 -B "$REPOSITORY/scripts/repository_state.py" fingerprint --root "$REPOSITORY")" ]] || \
    die 'prepare safety 검사가 source fingerprint를 변경했습니다.'
[[ "$BASE_LEARNER_SOURCE" == "$(python3 -B "$REPOSITORY/scripts/repository_state.py" fingerprint \
    --root "$REPOSITORY" --include-workspace)" ]] || \
    die 'prepare safety 검사가 학습자 workspace를 변경했습니다.'
[[ "$BASE_RAW_INDEX" == "$(raw_index_hash)" ]] || \
    die 'prepare safety 검사가 raw Git index bytes를 변경했습니다.'
[[ -z "$(git -C "$REPOSITORY" status --porcelain --untracked-files=all)" ]] || \
    die 'prepare safety 검사가 source/index 상태를 변경했습니다.'

printf 'PREPARE SAFETY: PASS (workspace preserved, exclusive temp, tool probes, symlink fail-closed, signal cleanup)\n'
