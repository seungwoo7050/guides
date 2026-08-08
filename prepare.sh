#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$SCRIPT_DIR"

say()
{
    printf '\n============================================================\n'
    printf '%s\n' "$1"
    printf '============================================================\n'
}

die()
{
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

command_exists()
{
    command -v "$1" >/dev/null 2>&1
}

pnpm_run()
{
    pnpm "$@"
}

[ -f package.json ] || die "저장소 루트에서 실행해야 합니다."
[ -f .nvmrc ] || die ".nvmrc가 없습니다."
[ -f scripts/verify-guide-structure.mjs ] || die "guide-web-applications 저장소로 보이지 않습니다."

say "1/7 시스템 도구 확인"
command_exists git || die "git을 찾을 수 없습니다."
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "Git 저장소 안에서 실행해야 합니다."
GIT_ROOT=$(CDPATH= cd -- "$GIT_ROOT" && pwd -P)
[ "$GIT_ROOT" = "$SCRIPT_DIR" ] || die "저장소 루트의 prepare.sh를 실행해야 합니다: $GIT_ROOT"

command_exists node || die "Node.js를 찾을 수 없습니다. Node.js 24.19.0 이상 25 미만을 설치한 뒤 다시 실행하십시오."
node - <<'NODE' || die "Node.js 24.19.0 이상 25 미만이 필요합니다. 현재 버전: $(node --version)"
const [major, minor] = process.versions.node.split(".").map(Number);
if (major !== 24 || minor < 19) process.exit(1);
NODE

command_exists docker || die "docker를 찾을 수 없습니다. Docker Engine 또는 Docker Desktop을 설치하십시오."
docker info >/dev/null 2>&1 || die "Docker daemon에 연결할 수 없습니다. Docker를 시작한 뒤 다시 실행하십시오."
docker compose version >/dev/null 2>&1 || die "docker compose plugin을 사용할 수 없습니다."

EXPECTED_PNPM=$(node -p 'require("./package.json").packageManager.split("@").at(-1)')
rm -rf -- "$SCRIPT_DIR/.guide-tools"
hash -r 2>/dev/null || true
PNPM_PROVIDER=
PNPM_EXECUTABLE=

if command_exists pnpm && [ "$(pnpm --version 2>/dev/null || true)" = "$EXPECTED_PNPM" ]; then
    PNPM_PROVIDER=direct
    PNPM_EXECUTABLE=$(command -v pnpm)
elif command_exists corepack && [ "$(corepack pnpm --version 2>/dev/null || true)" = "$EXPECTED_PNPM" ]; then
    PNPM_PROVIDER=corepack
    PNPM_EXECUTABLE=$(command -v corepack)
else
    die "pnpm $EXPECTED_PNPM를 실행할 수 없습니다. packageManager 선언을 지원하는 Corepack 또는 같은 버전의 pnpm을 준비하십시오."
fi

TOOLS_BIN="$SCRIPT_DIR/.guide-tools/bin"
mkdir -p "$TOOLS_BIN"
{
    printf '%s\n' '#!/bin/sh'
    if [ "$PNPM_PROVIDER" = "direct" ]; then
        printf 'exec "%s" "$@"\n' "$PNPM_EXECUTABLE"
    else
        printf 'exec "%s" pnpm "$@"\n' "$PNPM_EXECUTABLE"
    fi
} > "$TOOLS_BIN/pnpm"
chmod +x "$TOOLS_BIN/pnpm"
PATH="$TOOLS_BIN:$PATH"
export PATH
[ "$(pnpm --version)" = "$EXPECTED_PNPM" ] || die "저장소 전용 pnpm 실행기를 준비하지 못했습니다."

printf '[OK] node %s\n' "$(node --version)"
printf '[OK] pnpm %s\n' "$(pnpm --version)"
printf '[OK] docker %s\n' "$(docker --version)"
printf '[OK] %s\n' "$(docker compose version)"

say "2/7 최종 파일 구조 준비"
REQUIRED_NEW_PATHS='
.nvmrc
docs/00-roadmap.md
docs/01-web-foundations/01-how-the-web-works.md
docs/01-web-foundations/08-node-packages-workspaces.md
docs/02-frontend/01-react-components-state.md
docs/03-backend/01-http-api-model.md
docs/04-data-and-security/01-sql-relational-model.md
docs/05-realtime-and-quality/01-websocket-protocol.md
docs/06-capstones/04-collaboration-board.md
exercises/collaboration-board/README.md
scripts/verify-exercise-contracts.mjs
scripts/verify-checker-quality.mjs
prepare.sh
verify.sh
'

printf '%s\n' "$REQUIRED_NEW_PATHS" | while IFS= read -r relative
do
    [ -n "$relative" ] || continue
    [ -e "$relative" ] || die "필수 경로가 없습니다: $relative"
done

OBSOLETE_PATHS='
docs/00-javascript-typescript-foundations.md
docs/01-runtime-and-workspace.md
docs/02-browser-ui-platform.md
docs/03-react-nextjs-frontend.md
docs/04-fastify-zod-api.md
docs/05-postgresql-kysely.md
docs/06-auth-security.md
docs/07-realtime-websocket-canvas.md
docs/08-testing-quality.md
docs/09-collaboration-board.md
prepare-verify.sh
make-out.txt
'

printf '%s\n' "$OBSOLETE_PATHS" | while IFS= read -r relative
do
    [ -n "$relative" ] || continue
    if [ -e "$relative" ]; then
        rm -rf -- "$relative"
        printf '[DELETE] %s\n' "$relative"
    fi
done

printf '%s\n' "$OBSOLETE_PATHS" | while IFS= read -r relative
do
    [ -n "$relative" ] || continue
    [ ! -e "$relative" ] || die "이전 경로를 제거하지 못했습니다: $relative"
done

chmod +x prepare.sh verify.sh
node scripts/clean-generated.mjs

say "3/7 workspace 의존성 설치"
pnpm_run install --frozen-lockfile

(
    cd exercises/01-runtime/reference
    pnpm_run --filter @exercise/demo exec tsc --version >/dev/null
)

for project in \
    exercises/03-react-nextjs/reference \
    exercises/04-fastify-zod-api/reference \
    exercises/05-postgresql-kysely/reference \
    exercises/06-security/reference \
    exercises/07-websocket/reference \
    exercises/08-testing/reference \
    projects/collaboration-board
do
    [ -f "$project/package.json" ] || die "package.json 누락: $project"
    (cd "$project" && pnpm_run exec tsc --version >/dev/null)
done
printf '[OK] TypeScript 실행 환경을 확인했습니다.\n'

say "4/7 Playwright Chromium 준비"
for project in exercises/08-testing/reference projects/collaboration-board
do
    (cd "$project" && pnpm_run exec playwright install chromium)
done
PLAYWRIGHT_CHROMIUM=$(cd exercises/08-testing/reference && \
    pnpm_run exec node -e 'const { chromium } = require("@playwright/test"); process.stdout.write(chromium.executablePath())')
[ -x "$PLAYWRIGHT_CHROMIUM" ] || die "설치된 Playwright Chromium 실행 파일을 찾을 수 없습니다: $PLAYWRIGHT_CHROMIUM"
printf '[OK] Chromium %s\n' "$PLAYWRIGHT_CHROMIUM"

say "5/7 PostgreSQL 테스트 이미지 준비"
COMPOSE_FILE=exercises/05-postgresql-kysely/compose.test.yml
[ -f "$COMPOSE_FILE" ] || die "Compose 파일이 없습니다: $COMPOSE_FILE"
docker compose -f "$COMPOSE_FILE" pull postgres

say "6/7 준비 상태의 최소 구조 확인"
node scripts/verify-guide-structure.mjs
node scripts/verify-links.mjs

say "7/7 완료"
printf 'PREPARE RESULT: PASS\n'
printf '저장소가 전체 검증 가능한 상태로 준비되었습니다.\n'
printf '다음 명령을 실행하십시오:\n\n    ./verify.sh\n\n'
