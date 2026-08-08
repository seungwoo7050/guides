import { cp, mkdtemp, mkdir, readdir, readFile, rm, stat, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";

const root = path.resolve(new URL("..", import.meta.url).pathname);
const author = "Seungwoo Kim <seungwoo7050@naver.com>";
const exerciseMetadata = [
  ["01-runtime", "Tue, 26 Aug 2025 19:12:00 +0900", "feat(runtime): 실행 환경과 작업 공간 구성"],
  ["02-browser", "Thu, 4 Sep 2025 20:08:00 +0900", "feat(browser): 접근 가능한 브라우저 화면 구현"],
  ["03-react-nextjs", "Sun, 7 Sep 2025 16:22:00 +0900", "feat(frontend): React와 Next.js 화면 구현"],
  ["04-fastify-zod-api", "Mon, 22 Sep 2025 20:37:00 +0900", "feat(api): Fastify API 계약 구현"],
  ["05-postgresql-kysely", "Tue, 30 Sep 2025 21:16:00 +0900", "feat(data): PostgreSQL 트랜잭션 구현"],
  ["06-security", "Tue, 7 Oct 2025 20:49:00 +0900", "fix(security): 세션과 권한 경계 보완"],
  ["07-websocket", "Wed, 15 Oct 2025 21:31:00 +0900", "feat(realtime): WebSocket 상태 동기화 구현"],
  ["08-testing", "Thu, 23 Oct 2025 20:26:00 +0900", "test(web): 기능별 검사 경계 구성"]
];
const collaborationBoardMetadata = [
  ["Tue, 26 Aug 2025 19:18:00 +0900", "chore(board): 실행 환경과 작업 공간 구성"],
  ["Thu, 4 Sep 2025 20:42:00 +0900", "feat(board): 보드 화면 골격 추가"],
  ["Sun, 7 Sep 2025 17:07:00 +0900", "feat(board): 보드 목록과 화면 상태 추가"],
  ["Mon, 22 Sep 2025 20:35:00 +0900", "feat(api): HTTP 계약과 메모리 저장소 추가"],
  ["Tue, 30 Sep 2025 20:54:00 +0900", "feat(data): PostgreSQL 영속화와 트랜잭션 추가"],
  ["Tue, 7 Oct 2025 20:49:00 +0900", "feat(security): 세션과 역할 기반 권한 추가"],
  ["Wed, 15 Oct 2025 21:31:00 +0900", "feat(realtime): 실시간 스냅숏과 패치 동기화 추가"],
  ["Sun, 9 Nov 2025 12:45:00 +0900", "test(board): 통합 검사와 브라우저 흐름 추가"]
];
const collaborationBoardReadmes = [
  `# 실시간 협업 보드

Fastify API와 Next.js 화면을 한 pnpm 작업 공간에서 개발하기 위한 골격을 구성했습니다. Node.js 24와 pnpm 10을 사용합니다.

\`\`\`sh
pnpm install --frozen-lockfile
\`\`\`
`,
  `# 실시간 협업 보드

Fastify API와 Next.js 화면을 한 pnpm 작업 공간에서 개발합니다. 공통 레이아웃은 키보드로 건너뛸 수 있는 링크와 현재 위치를 알리는 탐색 구조를 제공합니다.

\`\`\`sh
pnpm install --frozen-lockfile
pnpm --filter @board/web dev
\`\`\`
`,
  `# 실시간 협업 보드

Next.js 화면에서 보드 목록과 활동 내역을 조회합니다. 서버 응답은 별도 어댑터에서 읽으며, 로딩 중인 화면과 찾을 수 없는 경로를 구분합니다.

\`\`\`sh
pnpm install --frozen-lockfile
pnpm --filter @board/web typecheck
pnpm --filter @board/web dev
\`\`\`
`,
  `# 실시간 협업 보드

Fastify API와 Next.js 화면이 같은 Zod 스키마를 사용합니다. 메모리 저장소로 로그인과 보드 생성·조회 흐름을 실행할 수 있습니다.

\`\`\`sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm dev
\`\`\`
`,
  `# 실시간 협업 보드

Fastify와 Next.js로 구성한 협업 보드입니다. PostgreSQL 변경은 Kysely 트랜잭션으로 저장합니다.

\`\`\`sh
docker compose -f compose.dev.yml up -d
cp .env.example .env
pnpm install --frozen-lockfile
pnpm --filter @board/db migrate
pnpm dev
\`\`\`

마이그레이션은 사용자, 보드, 항목, 활동 내역을 함께 준비합니다. 저장소 단위 검사는 실제 PostgreSQL 주소가 있을 때 트랜잭션 경로도 실행합니다.
`,
  `# 실시간 협업 보드

쿠키 세션과 역할 기반 권한을 적용한 협업 보드입니다. 로그인하지 않은 요청과 권한이 없는 요청은 각각 \`401\`, \`403\`으로 구분하며, 관리 작업은 별도 기록으로 남깁니다.

\`\`\`sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm build
\`\`\`

PostgreSQL 경로는 \`docker compose -f compose.dev.yml up -d\`로 준비한 뒤 \`.env.example\`을 \`.env\`로 복사해 실행합니다.
`,
  `# 실시간 협업 보드

HTTP로 저장한 보드 상태를 WebSocket으로 여러 사용자에게 전달합니다. 접속할 때 세션과 역할을 다시 확인하고, 오래된 버전의 변경은 최신 스냅숏으로 복구합니다.

\`\`\`sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test
pnpm build
\`\`\`

PostgreSQL 경로는 \`docker compose -f compose.dev.yml up -d\`로 준비합니다. 브로커 없이 API 인스턴스 안에서 연결을 관리하므로 여러 인스턴스로 확장할 때는 외부 전달 계층이 필요합니다.
`
];

await generateExercisePatches();
await generateCollaborationBoardPatches();

async function generateExercisePatches() {
  for (const [name, date, subject] of exerciseMetadata) {
    const directory = path.join(root, "exercises", name);
    const temp = await mkdtemp(path.join(tmpdir(), `${name}-patch-`));
    try {
      const oldTree = path.join(temp, "old");
      const newTree = path.join(temp, "new");
      await cp(path.join(directory, "skeleton"), oldTree, { recursive: true, filter: includeSource });
      await cp(path.join(directory, "reference"), newTree, { recursive: true, filter: includeSource });
      const diff = diffTrees(oldTree, newTree);
      await writeFile(path.join(directory, "reference.patch"), message(date, `[PATCH] ${subject}`, diff));
    } finally {
      await rm(temp, { recursive: true, force: true });
    }
  }
}

async function generateCollaborationBoardPatches() {
  const collaborationBoard = path.join(root, "exercises", "collaboration-board");
  const reference = path.join(root, "projects", "collaboration-board");
  const temp = await mkdtemp(path.join(tmpdir(), "board-patch-stages-"));
  try {
    let previous = path.join(temp, "stage-00");
    await cp(path.join(collaborationBoard, "skeleton"), previous, { recursive: true });
    const files = await walk(reference);
    for (let stage = 1; stage <= 8; stage += 1) {
      const next = path.join(temp, `stage-${String(stage).padStart(2, "0")}`);
      await cp(previous, next, { recursive: true });
      for (const file of files) {
        const relative = path.relative(reference, file);
        if (stageFor(relative) !== stage) continue;
        const target = path.join(next, relative);
        await mkdir(path.dirname(target), { recursive: true });
        await cp(file, target);
      }
      const readme =
        stage === 8
          ? await readFile(path.join(reference, "README.md"), "utf8")
          : collaborationBoardReadmes[stage - 1];
      await writeFile(path.join(next, "README.md"), readme);
      const [date, subject] = collaborationBoardMetadata[stage - 1];
      const diff = diffTrees(previous, next);
      await writeFile(
        path.join(collaborationBoard, "patches", `${String(stage).padStart(2, "0")}-${patchName(stage)}.patch`),
        message(date, `[PATCH ${stage}/8] ${subject}`, diff)
      );
      previous = next;
    }
  } finally {
    await rm(temp, { recursive: true, force: true });
  }
}

function stageFor(relative) {
  if (relative === "README.md") return Number.POSITIVE_INFINITY;
  if (
    [".gitignore", "package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml", "tsconfig.base.json"].includes(relative) ||
    /^(apps|packages)\/[^/]+\/(package|tsconfig)\.json$/.test(relative) ||
    relative === "apps/web/next.config.mjs"
  ) return 1;
  if (
    relative === "apps/web/app/globals.css" ||
    relative === "apps/web/app/layout.tsx" ||
    relative === "apps/web/app/loading.tsx" ||
    relative === "apps/web/app/not-found.tsx" ||
    relative === "apps/web/components/AppShell.tsx" ||
    relative === "apps/web/postcss.config.mjs" ||
    relative === "apps/web/tailwind.config.ts"
  ) return 2;
  if (
    relative === "apps/web/app/page.tsx" ||
    relative === "apps/web/app/activity/page.tsx" ||
    relative === "apps/web/components/BoardList.tsx" ||
    relative === "apps/web/components/LoginForm.tsx" ||
    relative === "apps/web/lib/api.ts"
  ) return 3;
  if (
    relative.startsWith("packages/contracts/src/") && !relative.endsWith(".test.ts") ||
    relative === "packages/db/src/index.ts"
  ) return 4;
  if (
    relative === ".env.example" ||
    relative === "compose.dev.yml" ||
    relative === "packages/db/migrations/001_initial.sql" ||
    ["cli.ts", "db-types.ts", "migrate.ts", "postgres.ts"].some((name) => relative === `packages/db/src/${name}`)
  ) return 5;
  if (
    relative === "apps/api/src/app.ts" ||
    relative === "apps/api/src/index.ts" ||
    relative === "apps/web/app/admin/page.tsx"
  ) return 6;
  if (
    relative === "apps/api/src/boardHub.ts" ||
    relative === "apps/web/components/BoardCanvas.tsx" ||
    relative === "apps/web/app/boards/[id]/page.tsx"
  ) return 7;
  return 8;
}

function patchName(stage) {
  return ["runtime", "browser", "react-nextjs", "fastify-zod-api", "postgresql-kysely", "security", "websocket", "testing"][stage - 1];
}

function includeSource(source) {
  return !source.endsWith(".tsbuildinfo") && path.basename(source) !== "next-env.d.ts" &&
    !source.split(path.sep).some((part) =>
      ["node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(part)
    );
}

function diffTrees(oldDirectory, newDirectory) {
  const parent = path.dirname(oldDirectory);
  const oldName = path.basename(oldDirectory);
  const newRelative = path.relative(parent, newDirectory);
  const result = spawnSync(
    "git",
    ["diff", "--no-index", "--binary", "--", oldName, newRelative],
    { cwd: parent, encoding: "utf8", maxBuffer: 32 * 1024 * 1024 }
  );
  if (![0, 1].includes(result.status ?? -1)) {
    throw new Error(`git diff 실패\n${result.stdout}\n${result.stderr}`);
  }
  return result.stdout
    .replaceAll(`a/${oldName}/`, "a/")
    .replaceAll(`a/${newRelative}/`, "a/")
    .replaceAll(`b/${oldName}/`, "b/")
    .replaceAll(`b/${newRelative}/`, "b/")
    .replace(/^ $/gm, "");
}

function message(date, subject, diff) {
  const id = createHash("sha1").update(`${date}\0${subject}\0${diff}`).digest("hex");
  return `From ${id} Mon Sep 17 00:00:00 2001\nFrom: ${author}\nDate: ${date}\nSubject: ${subject}\n\n${diff}--\n2.47.3\n`;
}

async function walk(directory) {
  const files = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (["node_modules", ".next", "coverage", "playwright-report", "test-results"].includes(entry.name)) continue;
    if (entry.isFile() && entry.name.endsWith(".tsbuildinfo")) continue;
    const full = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await walk(full));
    else if ((await stat(full)).isFile()) files.push(full);
  }
  return files.sort();
}
