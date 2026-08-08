#!/bin/sh

# guide-frontend-react-nextjs repository preparation
#
# Run once from the repository root after applying the overlay:
#   ./prepare.sh
#
# Responsibilities:
# - normalize the repository to the final file layout
# - remove files superseded by the final layout
# - remove stale generated output while preserving learner work
# - install the locked pnpm workspace dependencies
# - install the Playwright Chromium runtime used by verification
#
# This script deliberately does not run type checks, tests, builds, browser
# tests, smoke tests, or mutation checks. Those belong to ./verify.sh.

set -eu

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

require_path()
{
    path=$1
    [ -e "$path" ] || die "필수 경로가 없습니다: $path"
    printf '[OK] %s\n' "$path"
}

remove_obsolete_file()
{
    path=$1

    if [ -d "$path" ]; then
        die "삭제 대상으로 예상한 경로가 디렉터리입니다. 수동 확인이 필요합니다: $path"
    fi

    if [ -e "$path" ] || [ -L "$path" ]; then
        rm -f -- "$path"
        printf '[DELETE] %s\n' "$path"
    else
        printf '[SKIP] 이미 없음: %s\n' "$path"
    fi
}

cleanup_temporary()
{
    if [ -n "${PREPARE_TMPDIR:-}" ] && [ -d "$PREPARE_TMPDIR" ]; then
        rm -rf -- "$PREPARE_TMPDIR"
    fi
}

handle_prepare_signal()
{
    code=$1
    trap - EXIT HUP INT TERM
    cleanup_temporary
    exit "$code"
}

trap cleanup_temporary EXIT
trap 'handle_prepare_signal 129' HUP
trap 'handle_prepare_signal 130' INT
trap 'handle_prepare_signal 143' TERM

command_exists git || die "git을 찾을 수 없습니다."

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) ||
    die "Git 저장소 안에서 실행해야 합니다."

cd "$REPO_ROOT"

[ -f package.json ] || die "저장소 루트에 package.json이 없습니다."
[ -f pnpm-lock.yaml ] || die "저장소 루트에 pnpm-lock.yaml이 없습니다."
[ -f pnpm-workspace.yaml ] || die "저장소 루트에 pnpm-workspace.yaml이 없습니다."

PREPARE_TMPDIR=$(mktemp -d "${TMPDIR:-/tmp}/guide-frontend-prepare.XXXXXX") ||
    die "임시 디렉터리를 만들 수 없습니다."
MANIFEST_BEFORE="$PREPARE_TMPDIR/manifests.before"
MANIFEST_AFTER="$PREPARE_TMPDIR/manifests.after"

# ----------------------------------------------------------------------
# Overlay structure
# ----------------------------------------------------------------------

say "1/6 최종 오버레이 구조 확인"

REQUIRED_PATHS='
.gitignore
.nvmrc
Makefile
prepare.sh
verify.sh
README.md
CONTRIBUTING.md
package.json
pnpm-lock.yaml
pnpm-workspace.yaml
docs/00-roadmap-and-prerequisites.md
docs/01-project-onboarding.md
docs/02-ui-and-state-architecture.md
docs/03-nextjs-data-effects-and-concurrency.md
docs/04-testing-accessibility-and-performance.md
docs/05-production-runtime-contract.md
docs/90-practical-checklist.md
exercises/project-catalog/README.md
exercises/project-catalog/specs/01-project-onboarding.md
exercises/project-catalog/specs/02-ui-state-architecture.md
exercises/project-catalog/specs/03-data-effects-concurrency.md
exercises/project-catalog/specs/04-testing-accessibility-performance.md
exercises/project-catalog/specs/05-production-runtime-contract.md
exercises/project-catalog/reference/package.json
exercises/project-catalog/reference/playwright.config.ts
exercises/project-catalog/reference/scripts/run-playwright.mjs
exercises/project-catalog/reference/scripts/smoke-production.mjs
exercises/project-catalog/skeleton/README.md
exercises/project-catalog/create-workspace.mjs
exercises/project-catalog/check-workspace.mjs
exercises/project-catalog/check-stage-markers.mjs
scripts/clean-generated.mjs
scripts/snapshot-repository.mjs
scripts/verify-repository.mjs
scripts/verify-skeleton.mjs
scripts/verify-test-quality.mjs
'

printf '%s\n' "$REQUIRED_PATHS" |
while IFS= read -r path
do
    [ -n "$path" ] || continue
    require_path "$path"
done

# ----------------------------------------------------------------------
# Final layout
# ----------------------------------------------------------------------

say "2/6 대체된 파일과 이전 검증 산출물 제거"

OBSOLETE_FILES='
prepare-verify.sh
make-out.txt
docs/00-browser-and-react-foundations.md
docs/02-ui-architecture.md
docs/03-state-data-effects.md
docs/04-testing-performance-deployment.md
reference/practical-checklist.md
exercises/project-catalog/reference/tests/e2e/catalog.spec.ts
'

printf '%s\n' "$OBSOLETE_FILES" |
while IFS= read -r path
do
    [ -n "$path" ] || continue
    remove_obsolete_file "$path"
done

if [ -d reference ]; then
    rmdir reference 2>/dev/null || true
fi

printf '%s\n' "$OBSOLETE_FILES" |
while IFS= read -r path
do
    [ -n "$path" ] || continue
    [ ! -e "$path" ] && [ ! -L "$path" ] ||
        die "이전 경로가 남아 있습니다: $path"
done

command_exists node || die "node를 찾을 수 없습니다. Node.js 24.19.0 이상 25 미만이 필요합니다."
node scripts/clean-generated.mjs
printf '[OK] 이전 build/test 산출물을 제거했습니다.\n'

# ----------------------------------------------------------------------
# Runtime and package manager
# ----------------------------------------------------------------------

say "3/6 Node.js와 pnpm 준비"

node <<'NODE'
const [major, minor] = process.versions.node.split(".").map(Number);
if (major !== 24 || minor < 19) {
  console.error(`ERROR: Node.js 24.19.0 이상 25 미만이 필요합니다. 현재: ${process.version}`);
  process.exit(1);
}
const pkg = JSON.parse(require("node:fs").readFileSync("package.json", "utf8"));
if (pkg.packageManager !== "pnpm@10.32.1") {
  console.error(`ERROR: packageManager가 pnpm@10.32.1이 아닙니다: ${pkg.packageManager ?? "<missing>"}`);
  process.exit(1);
}
if (Object.prototype.hasOwnProperty.call(pkg.scripts ?? {}, "prepare")) {
  console.error("ERROR: package.json lifecycle prepare script는 pnpm install 중 ./prepare.sh를 재귀 실행할 수 있습니다.");
  process.exit(1);
}
NODE

EXPECTED_PNPM=10.32.1
CURRENT_PNPM=''
if command_exists pnpm; then
    CURRENT_PNPM=$(pnpm --version 2>/dev/null || true)
fi

if [ "$CURRENT_PNPM" != "$EXPECTED_PNPM" ]; then
    command_exists corepack ||
        die "pnpm $EXPECTED_PNPM을 찾을 수 없고 corepack도 없습니다. Node.js 배포의 corepack을 준비하십시오."

    printf '[INFO] corepack으로 pnpm %s를 준비합니다.\n' "$EXPECTED_PNPM"
    corepack prepare "pnpm@$EXPECTED_PNPM" --activate ||
        die "corepack이 pnpm $EXPECTED_PNPM을 활성화하지 못했습니다."

    if ! command_exists pnpm; then
        corepack enable >/dev/null 2>&1 || true
    fi
fi

command_exists pnpm || die "pnpm 명령을 활성화하지 못했습니다."
[ "$(pnpm --version)" = "$EXPECTED_PNPM" ] ||
    die "pnpm 버전이 일치하지 않습니다. 필요: $EXPECTED_PNPM, 현재: $(pnpm --version)"

printf 'node: %s\n' "$(node --version)"
printf 'pnpm: %s\n' "$(pnpm --version)"

# ----------------------------------------------------------------------
# Locked dependencies
# ----------------------------------------------------------------------

say "4/6 잠금 파일 기반 의존성 설치"

cksum package.json pnpm-lock.yaml pnpm-workspace.yaml > "$MANIFEST_BEFORE"
pnpm install --frozen-lockfile
cksum package.json pnpm-lock.yaml pnpm-workspace.yaml > "$MANIFEST_AFTER"

cmp -s "$MANIFEST_BEFORE" "$MANIFEST_AFTER" ||
    die "의존성 설치가 package.json 또는 잠금 파일을 변경했습니다."

[ -d exercises/project-catalog/reference/node_modules ] ||
    die "reference 의존성 디렉터리가 생성되지 않았습니다."

printf '[OK] 의존성 설치가 잠금 파일을 변경하지 않았습니다.\n'

# ----------------------------------------------------------------------
# Browser runtime
# ----------------------------------------------------------------------

say "5/6 Playwright Chromium 설치"

(
    cd exercises/project-catalog/reference
    pnpm exec playwright --version >/dev/null
    pnpm exec playwright install chromium
)

printf '[OK] Playwright Chromium 준비 완료\n'

# ----------------------------------------------------------------------
# Ready state
# ----------------------------------------------------------------------

say "6/6 검증 준비 상태 확인"

[ ! -e prepare-verify.sh ] || die "prepare-verify.sh가 남아 있습니다."
[ ! -e make-out.txt ] || die "이전 make-out.txt가 남아 있습니다."

if [ -d exercises/project-catalog/workspace ]; then
    printf '[INFO] 기존 학습자 workspace를 그대로 보존했습니다.\n'
else
    printf '[INFO] 학습자 workspace는 아직 없습니다. 필요할 때 pnpm exercise:create를 실행하십시오.\n'
fi

printf '\n[INFO] Git 기준\n'
printf 'branch: %s\n' "$(git branch --show-current 2>/dev/null || printf '<detached>')"
printf 'commit: %s\n' "$(git rev-parse HEAD)"

printf '\n[INFO] 준비 후 Git 상태\n'
git status --short

printf '\nPREPARE RESULT: PASS\n'
printf '저장소가 검증 가능한 최종 상태로 준비되었습니다.\n'
printf '다음 명령을 실행하십시오:\n\n'
printf '    ./verify.sh\n\n'
