#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
TMP=''
HOLD_PID=''
RACE_PID=''

cleanup() {
    local status=$?
    trap - EXIT HUP INT TERM
    for child in "$HOLD_PID" "$RACE_PID"; do
        if [[ -n "$child" ]]; then
            kill -TERM "$child" 2>/dev/null || true
            wait "$child" 2>/dev/null || true
        fi
    done
    if [[ -n "$TMP" && -d "$TMP" ]]; then
        rm -rf -- "$TMP"
    fi
    exit "$status"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

for command_name in git python3 bash; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "필수 명령을 찾지 못했습니다: $command_name" >&2
        exit 1
    fi
done

printf '%s\n' '[1/7] Markdown 구조와 로컬 링크'
python3 - "$ROOT" <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

root = Path(sys.argv[1]).resolve()
files = sorted(
    path for path in root.rglob('*.md')
    if path.relative_to(root).parts[:2] != ('exercises', 'workspace')
)
errors: list[str] = []
link_re = re.compile(r'(?<!!)\[[^\]]*\]\(([^)]+)\)')
heading_re = re.compile(r'^(#{1,6})\s+(.+?)\s*#*\s*$')
def github_slug(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('`', '').strip().lower()
    kept: list[str] = []
    for char in text:
        category = unicodedata.category(char)
        if char in {' ', '-'} or category[0] in {'L', 'N'} or char == '_':
            kept.append(char)
    return re.sub(r'\s+', '-', ''.join(kept))


def anchors_for(path: Path) -> set[str]:
    counts: dict[str, int] = {}
    anchors: set[str] = set()
    opened: tuple[str, int] | None = None
    for line in path.read_text(encoding='utf-8').splitlines():
        fence = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence:
            marker = fence.group(1)
            if opened is None:
                opened = (marker[0], len(marker))
            elif marker[0] == opened[0] and len(marker) >= opened[1]:
                opened = None
            continue
        if opened is not None:
            continue
        match = heading_re.match(line)
        if not match:
            continue
        base = github_slug(match.group(2))
        count = counts.get(base, 0)
        counts[base] = count + 1
        anchors.add(base if count == 0 else f'{base}-{count}')
    return anchors

anchor_cache: dict[Path, set[str]] = {}

for path in files:
    text = path.read_text(encoding='utf-8')
    rel = path.relative_to(root)

    opened: tuple[str, int, int, str] | None = None
    shell_lines: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        match = re.match(r'^\s*(`{3,}|~{3,})([^`]*)$', line)
        if opened is None:
            if not match:
                continue
            marker = match.group(1)
            language = match.group(2).strip().lower()
            opened = (marker[0], len(marker), line_no, language)
            shell_lines = []
            continue

        if match:
            marker = match.group(1)
            if marker[0] == opened[0] and len(marker) >= opened[1]:
                if opened[3] in {'bash', 'sh'}:
                    result = subprocess.run(
                        ['bash', '-n'],
                        input='\n'.join(shell_lines) + '\n',
                        text=True,
                        capture_output=True,
                    )
                    if result.returncode:
                        errors.append(
                            f'{rel}:{opened[2]}: 올바르지 않은 {opened[3]} 코드 블록: '
                            f'{result.stderr.strip()}'
                        )
                opened = None
                shell_lines = []
                continue

        if opened[3] in {'bash', 'sh'}:
            shell_lines.append(line)

    if opened is not None:
        errors.append(f'{rel}:{opened[2]}: unclosed fenced code block')

    for match in link_re.finditer(text):
        raw = match.group(1).strip()
        if raw.startswith('<') and raw.endswith('>'):
            raw = raw[1:-1]
        raw = raw.split(maxsplit=1)[0]
        if not raw or raw.startswith(('http://', 'https://', 'mailto:')):
            continue

        target_part, separator, fragment = raw.partition('#')
        if not target_part:
            resolved = path
        else:
            target = unquote(target_part)
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f'{rel}: local link escapes repository: {target}')
                continue
            if not resolved.exists():
                errors.append(f'{rel}: 로컬 링크 대상이 없습니다: {target}')
                continue

        if separator and fragment and resolved.suffix.lower() == '.md':
            expected = unquote(fragment)
            anchors = anchor_cache.setdefault(resolved, anchors_for(resolved))
            if expected not in anchors:
                errors.append(
                    f'{rel}: Markdown 앵커 #{expected}가 없습니다: '
                    f'{resolved.relative_to(root)}'
                )

if errors:
    print('\n'.join(errors), file=sys.stderr)
    raise SystemExit(1)
print(f'Markdown 문서 {len(files)}개를 검사했습니다')
PY

printf '%s\n' '[2/7] 셸 문법'
bash -n "$ROOT/exercises/setup.sh"
bash -n "$ROOT/scripts/validate.sh"

TMP=$(mktemp -d "${TMPDIR:-/tmp}/developer-guides-validate.XXXXXX")
mkdir -p "$TMP/exercises"
export GIT_CONFIG_GLOBAL="$TMP/global.gitconfig"
export GIT_CONFIG_NOSYSTEM=1
export GIT_TERMINAL_PROMPT=0
export GIT_PAGER=cat
export PAGER=cat
export GIT_EDITOR=true
export LC_ALL=C
cp "$ROOT/exercises/setup.sh" "$TMP/exercises/setup.sh"
chmod +x "$TMP/exercises/setup.sh"

printf '%s\n' '[3/7] 격리 저장소 생성과 범위별 초기화'
mkdir "$TMP/hold-tmp"
TMPDIR="$TMP/hold-tmp" GUIDE_WORKSPACE_TEST_HOLD=1 \
    GUIDE_WORKSPACE_TEST_READY_FILE="$TMP/hold-ready" \
    "$TMP/exercises/setup.sh" sample >"$TMP/hold.log" 2>&1 &
HOLD_PID=$!
lock_ready=0
for _ in $(seq 1 500); do
    if [[ -d "$TMP/exercises/.workspace.lock" && -s "$TMP/hold-ready" ]]; then
        lock_ready=1
        break
    fi
    kill -0 "$HOLD_PID" 2>/dev/null || break
    sleep 0.02
done
if [[ $lock_ready -ne 1 ]]; then
    kill -TERM "$HOLD_PID" 2>/dev/null || true
    wait "$HOLD_PID" 2>/dev/null || true
    HOLD_PID=''
    echo '완성된 staging과 setup concurrency lock을 관찰하지 못했습니다' >&2
    exit 1
fi
if "$TMP/exercises/setup.sh" sample >/dev/null 2>&1; then
    kill -TERM "$HOLD_PID" 2>/dev/null || true
    wait "$HOLD_PID" 2>/dev/null || true
    HOLD_PID=''
    echo '동시 setup이 lock을 우회했습니다' >&2
    exit 1
fi
kill -TERM "$HOLD_PID"
if wait "$HOLD_PID" 2>/dev/null; then
    HOLD_PID=''
    echo '중단된 setup이 성공 상태를 반환했습니다' >&2
    exit 1
fi
HOLD_PID=''
[[ ! -e "$TMP/exercises/.workspace.lock" ]]
[[ ! -e "$TMP/exercises/workspace" ]]
[[ -z $(find "$TMP/exercises" -maxdepth 1 -name '.workspace.tmp.*' -print -quit) ]]
[[ -z $(find "$TMP/hold-tmp" -maxdepth 1 -name 'git-guide-exercises.*' -print -quit) ]]

race_ready="$TMP/race-ready"
race_release="$TMP/race-release"
GUIDE_WORKSPACE_TEST_HOLD=1 GUIDE_WORKSPACE_TEST_READY_FILE="$race_ready" \
    GUIDE_WORKSPACE_TEST_RELEASE_FILE="$race_release" \
    "$TMP/exercises/setup.sh" sample >"$TMP/race.log" 2>&1 &
RACE_PID=$!
for _ in $(seq 1 500); do
    [[ -s "$race_ready" ]] && break
    kill -0 "$RACE_PID" 2>/dev/null || break
    sleep 0.02
done
if [[ ! -s "$race_ready" ]]; then
    kill -TERM "$RACE_PID" 2>/dev/null || true
    wait "$RACE_PID" 2>/dev/null || true
    RACE_PID=''
    echo 'destination race용 publish-ready 상태를 관찰하지 못했습니다' >&2
    exit 1
fi
mkdir "$TMP/exercises/workspace"
printf '%s\n' '경쟁 생성자가 보존할 파일' > "$TMP/exercises/workspace/sentinel"
touch "$race_release"
if wait "$RACE_PID" 2>/dev/null; then
    RACE_PID=''
    echo 'exclusive publish가 경쟁 destination을 덮어썼습니다' >&2
    exit 1
fi
RACE_PID=''
[[ "$(cat "$TMP/exercises/workspace/sentinel")" == '경쟁 생성자가 보존할 파일' ]]
[[ ! -e "$TMP/exercises/.workspace.lock" ]]
[[ -z $(find "$TMP/exercises" -maxdepth 1 -name '.workspace.tmp.*' -print -quit) ]]
rm -rf -- "$TMP/exercises/workspace"

mkdir "$TMP/external-workspace"
printf '%s\n' '보존할 파일' > "$TMP/external-workspace/sentinel"
ln -s "$TMP/external-workspace" "$TMP/exercises/workspace"
set +e
"$TMP/exercises/setup.sh" --reset all >/dev/null 2>&1
symlink_status=$?
set -e
if [[ $symlink_status -eq 0 || ! -e "$TMP/external-workspace/sentinel" ]]; then
    echo '설정 스크립트가 심볼릭 링크 작업 공간을 거부해야 합니다' >&2
    exit 1
fi
rm -f -- "$TMP/exercises/workspace"

"$TMP/exercises/setup.sh" sample >/dev/null 2>&1
[[ -d "$TMP/exercises/workspace/sample-app/.git" ]]
[[ ! -e "$TMP/exercises/workspace/team-app-dev-a" ]]

"$TMP/exercises/setup.sh" team >/dev/null 2>&1
[[ -d "$TMP/exercises/workspace/team-app-dev-a/.git" ]]
[[ -d "$TMP/exercises/workspace/team-app-dev-b/.git" ]]
[[ -d "$TMP/exercises/workspace/team-app-maintainer/.git" ]]

set +e
"$TMP/exercises/setup.sh" sample >/dev/null 2>&1
create_again_status=$?
set -e
if [[ $create_again_status -eq 0 ]]; then
    echo '설정 스크립트가 기존 실습 환경의 덮어쓰기를 거부해야 합니다' >&2
    exit 1
fi

printf '%s\n' '협업 환경 보존' > "$TMP/exercises/workspace/team-app-dev-a/.team-marker"
printf '%s\n' '실습 환경 제거' > "$TMP/exercises/workspace/sample-app/.sample-marker"
"$TMP/exercises/setup.sh" --reset sample >/dev/null 2>&1
[[ ! -e "$TMP/exercises/workspace/sample-app/.sample-marker" ]]
[[ -e "$TMP/exercises/workspace/team-app-dev-a/.team-marker" ]]

printf '%s\n' '실습 환경 보존' > "$TMP/exercises/workspace/sample-app/.sample-marker"
"$TMP/exercises/setup.sh" --reset team >/dev/null 2>&1
[[ -e "$TMP/exercises/workspace/sample-app/.sample-marker" ]]
[[ ! -e "$TMP/exercises/workspace/team-app-dev-a/.team-marker" ]]

"$TMP/exercises/setup.sh" --reset all >/dev/null 2>&1
[[ ! -e "$TMP/exercises/workspace/sample-app/.sample-marker" ]]

EXERCISE="$TMP/exercises/workspace"
SAMPLE="$EXERCISE/sample-app"
A="$EXERCISE/team-app-dev-a"
B="$EXERCISE/team-app-dev-b"
M="$EXERCISE/team-app-maintainer"
REMOTE="$EXERCISE/remotes/team-app.git"

printf '%s\n' '[4/7] 기준 상태 검사'
"$SAMPLE/scripts/test.sh" >/dev/null
"$A/scripts/check.sh" >/dev/null
"$B/scripts/check.sh" >/dev/null
"$M/scripts/check.sh" >/dev/null
[[ -z $(git -C "$SAMPLE" status --porcelain) ]]
[[ -z $(git -C "$A" status --porcelain) ]]

printf '%s\n' '[5/7] 변경 조각 선택과 목적별 커밋 분리'
git -C "$SAMPLE" switch --no-track -c feature/title-validation origin/main >/dev/null
cat > "$SAMPLE/src/validate_title.sh" <<'SOURCE'
#!/usr/bin/env sh

is_valid_title()
{
    [ "$#" -eq 1 ] || return 1

    title=$1
    length=${#title}

    [ "$length" -ge 3 ] && [ "$length" -le 60 ]
}
SOURCE
cat > "$SAMPLE/tests/test_validate_title.sh" <<'TEST'
#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
. "$ROOT/src/validate_title.sh"

expect_valid()
{
    is_valid_title "$1" || {
        echo "허용해야 하는 제목입니다: $1" >&2
        exit 1
    }
}

expect_invalid()
{
    if is_valid_title "$1"; then
        echo "거부해야 하는 제목입니다: $1" >&2
        exit 1
    fi
}

expect_valid "로그인 리다이렉트 수정"
expect_invalid ""
expect_invalid "ab"
expect_invalid "1234567890123456789012345678901234567890123456789012345678901"
printf '%s\n' '제목 검증 통과'
TEST
chmod +x "$SAMPLE/src/validate_title.sh" "$SAMPLE/tests/test_validate_title.sh"
python3 - "$SAMPLE/README.md" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
text = text.replace(
    '현재 실습 fixture는 비어 있지 않은 모든 제목을 허용합니다.',
    '제목은 3자 이상 60자 이하여야 합니다.',
)
text = text.replace('의존썽', '의존성')
path.write_text(text)
PY
mkdir -p "$SAMPLE/notes"
printf '%s\n' '유니코드 경계 사례를 추가로 확인' > "$SAMPLE/notes/debug.txt"

"$SAMPLE/scripts/test.sh" >/dev/null
git -C "$SAMPLE" add src/validate_title.sh tests/test_validate_title.sh
printf 'y\nn\n' | git -C "$SAMPLE" -c color.ui=false add -p README.md >/dev/null

git -C "$SAMPLE" diff --cached --check
git -C "$SAMPLE" diff --cached -- README.md | grep -Fq '제목은 3자 이상 60자 이하여야 합니다.'
! git -C "$SAMPLE" diff --cached -- README.md | grep -Fq '외부 의존성이 없습니다.'
git -C "$SAMPLE" diff -- README.md | grep -Fq '외부 의존성이 없습니다.'
[[ -e "$SAMPLE/notes/debug.txt" ]]
[[ $(git -C "$SAMPLE" status --porcelain --untracked-files=all | grep -c '^?? notes/debug.txt$') -eq 1 ]]

git -C "$SAMPLE" commit -m 'feat: 작업 제목 길이 검증' >/dev/null
git -C "$SAMPLE" add README.md
git -C "$SAMPLE" diff --cached --check
git -C "$SAMPLE" commit -m 'docs: 의존성 표기 수정' >/dev/null
[[ $(git -C "$SAMPLE" rev-list --count origin/main..HEAD) -eq 2 ]]
[[ $(git -C "$SAMPLE" status --porcelain --untracked-files=all | grep -c '^?? notes/debug.txt$') -eq 1 ]]
rm -rf -- "$SAMPLE/notes"
[[ -z $(git -C "$SAMPLE" status --porcelain) ]]

printf '%s\n' '[6/7] rebase 충돌, 일반 푸시 거부와 lease 보호 갱신'
git -C "$B" switch --no-track -c feature/add-assignee origin/main >/dev/null
cat > "$B/config/task-fields.yml" <<'CONFIG'
fields:
  - title
  - status
  - assignee
CONFIG
"$B/scripts/check.sh" >/dev/null
git -C "$B" add config/task-fields.yml
git -C "$B" commit -m 'feat: 담당자 필드 추가' >/dev/null
git -C "$B" push -u origin HEAD >/dev/null

git -C "$A" switch --no-track -c feature/add-priority origin/main >/dev/null
cat > "$A/config/task-fields.yml" <<'CONFIG'
fields:
  - title
  - status
  - priority
CONFIG
"$A/scripts/check.sh" >/dev/null
git -C "$A" add config/task-fields.yml
git -C "$A" commit -m 'feat: 우선순위 필드 추가' >/dev/null
git -C "$A" push -u origin HEAD >/dev/null

git -C "$M" fetch origin >/dev/null
git -C "$M" switch main >/dev/null
git -C "$M" merge --ff-only origin/main >/dev/null
git -C "$M" merge --no-ff origin/feature/add-priority -m 'merge: 우선순위 필드 통합' >/dev/null
"$M/scripts/check.sh" >/dev/null
git -C "$M" push origin HEAD:main >/dev/null

git -C "$B" fetch origin >/dev/null
old_sha=$(git -C "$B" rev-parse HEAD)
set +e
git -C "$B" rebase origin/main >/dev/null 2>&1
rebase_status=$?
set -e
if [[ $rebase_status -eq 0 ]]; then
    echo '예상한 rebase 충돌이 발생하지 않았습니다' >&2
    exit 1
fi
grep -Eq '^(<<<<<<<|=======|>>>>>>>)' "$B/config/task-fields.yml"
cat > "$B/config/task-fields.yml" <<'CONFIG'
fields:
  - title
  - status
  - priority
  - assignee
CONFIG
git -C "$B" add config/task-fields.yml
GIT_EDITOR=true git -C "$B" rebase --continue >/dev/null
new_sha=$(git -C "$B" rev-parse HEAD)
[[ "$old_sha" != "$new_sha" ]]
"$B/scripts/check.sh" >/dev/null
[[ -z $(git -C "$B" status --porcelain) ]]

set +e
git -C "$B" push origin HEAD:feature/add-assignee >/dev/null 2>&1
push_status=$?
set -e
if [[ $push_status -eq 0 ]]; then
    echo '예상한 비선형 푸시 거부가 발생하지 않았습니다' >&2
    exit 1
fi

git -C "$B" push --force-with-lease origin HEAD:feature/add-assignee >/dev/null
local_sha=$(git -C "$B" rev-parse HEAD)
remote_sha=$(git --git-dir="$REMOTE" rev-parse refs/heads/feature/add-assignee)
[[ "$local_sha" == "$remote_sha" ]]

printf '%s\n' '[7/7] reflog·detached HEAD·revert·stash·bisect 복구'

RECOVERY="$TMP/recovery"
git init -q "$RECOVERY"
git -C "$RECOVERY" config user.name 'Guide Test'
git -C "$RECOVERY" config user.email 'guide@example.invalid'
printf 'base\n' >"$RECOVERY/state.txt"
git -C "$RECOVERY" add state.txt
git -C "$RECOVERY" commit -q -m 'base'
git -C "$RECOVERY" branch -M main

printf 'reflog target\n' >"$RECOVERY/reflog.txt"
git -C "$RECOVERY" add reflog.txt
git -C "$RECOVERY" commit -q -m 'reflog target'
reflog_target=$(git -C "$RECOVERY" rev-parse HEAD)
git -C "$RECOVERY" reset --hard HEAD^ >/dev/null
! git -C "$RECOVERY" branch --contains "$reflog_target" | grep -q . ||
    { echo 'reset한 커밋이 브랜치에 남았습니다' >&2; exit 1; }
git -C "$RECOVERY" reflog --format=%H | grep -Fqx "$reflog_target"
git -C "$RECOVERY" branch recovery/reflog "$reflog_target"
[[ $(git -C "$RECOVERY" show recovery/reflog:reflog.txt) == 'reflog target' ]]

git -C "$RECOVERY" switch --detach main >/dev/null
printf 'detached\n' >"$RECOVERY/detached.txt"
git -C "$RECOVERY" add detached.txt
git -C "$RECOVERY" commit -q -m 'detached target'
detached_target=$(git -C "$RECOVERY" rev-parse HEAD)
git -C "$RECOVERY" switch main >/dev/null
! git -C "$RECOVERY" branch --contains "$detached_target" | grep -q . ||
    { echo 'detached 커밋이 예상과 달리 브랜치에 포함되었습니다' >&2; exit 1; }
git -C "$RECOVERY" branch recovery/detached "$detached_target"
[[ $(git -C "$RECOVERY" show recovery/detached:detached.txt) == 'detached' ]]

tree_before=$(git -C "$RECOVERY" write-tree)
printf 'temporary change\n' >"$RECOVERY/revert.txt"
git -C "$RECOVERY" add revert.txt
git -C "$RECOVERY" commit -q -m 'change to revert'
git -C "$RECOVERY" revert --no-edit HEAD >/dev/null
tree_after=$(git -C "$RECOVERY" write-tree)
[[ "$tree_before" == "$tree_after" ]]

printf 'tracked edit\n' >>"$RECOVERY/state.txt"
printf 'untracked\n' >"$RECOVERY/untracked.txt"
git -C "$RECOVERY" stash push -u -m 'recovery check' >/dev/null
[[ -z $(git -C "$RECOVERY" status --porcelain) ]]
git -C "$RECOVERY" stash apply --index >/dev/null
grep -Fqx 'tracked edit' "$RECOVERY/state.txt"
grep -Fqx 'untracked' "$RECOVERY/untracked.txt"
git -C "$RECOVERY" reset --hard HEAD >/dev/null
git -C "$RECOVERY" clean -fd >/dev/null
git -C "$RECOVERY" stash drop >/dev/null

BISECT="$TMP/bisect"
git init -q "$BISECT"
git -C "$BISECT" config user.name 'Guide Test'
git -C "$BISECT" config user.email 'guide@example.invalid'
cat >"$BISECT/check-value.sh" <<'CHECK_VALUE'
#!/bin/sh
set -eu
[ "$(cat value.txt)" -lt 9 ]
CHECK_VALUE
chmod +x "$BISECT/check-value.sh"
printf '1\n' >"$BISECT/value.txt"
git -C "$BISECT" add check-value.sh value.txt
git -C "$BISECT" commit -q -m 'good baseline'
bisect_good=$(git -C "$BISECT" rev-parse HEAD)
for value in 3 6 9 12 15; do
    printf '%s\n' "$value" >"$BISECT/value.txt"
    git -C "$BISECT" add value.txt
    git -C "$BISECT" commit -q -m "set value $value"
    if [[ "$value" -eq 9 ]]; then
        bisect_bad=$(git -C "$BISECT" rev-parse HEAD)
    fi
done
git -C "$BISECT" bisect start HEAD "$bisect_good" >/dev/null
git -C "$BISECT" bisect run ./check-value.sh >/dev/null
[[ $(git -C "$BISECT" rev-parse refs/bisect/bad) == "$bisect_bad" ]]
git -C "$BISECT" bisect reset >/dev/null

printf '%s\n' 'Git 문서와 실습 검사 통과'
