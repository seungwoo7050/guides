import { access, readFile } from "node:fs/promises";
import path from "node:path";

const root = path.resolve(new URL("../exercises/collaboration-board/reference", import.meta.url).pathname);
const required = [
  "package.json",
  "pnpm-workspace.yaml",
  "apps/web/package.json",
  "apps/api/package.json",
  "packages/contracts/package.json",
  "packages/db/package.json",
  "packages/db/migrations/001_initial.sql",
  "apps/api/src/app.ts",
  "apps/api/src/boardHub.ts",
  "apps/web/app/boards/[id]/page.tsx",
  "tests/e2e/board.spec.ts",
  "tests/smoke.mjs"
];
for (const file of required) await access(path.join(root, file));

const pkg = JSON.parse(await readFile(path.join(root, "package.json"), "utf8"));
for (const script of ["dev", "typecheck", "build", "test", "test:e2e", "smoke"]) {
  if (typeof pkg.scripts?.[script] !== "string") throw new Error(`누락된 명령: ${script}`);
}

const migration = await readFile(path.join(root, "packages/db/migrations/001_initial.sql"), "utf8");
for (const table of [
  "users",
  "sessions",
  "boards",
  "board_members",
  "board_items",
  "board_events",
  "admin_actions"
]) {
  if (!migration.includes(`table if not exists ${table}`)) throw new Error(`누락된 테이블: ${table}`);
}

const contracts = await readFile(path.join(root, "packages/contracts/src/ws.ts"), "utf8");
for (const event of [
  "board.join",
  "cursor.move",
  "item.create",
  "item.update",
  "item.move",
  "snapshot.request",
  "board.snapshot",
  "board.patch",
  "presence.changed",
  "board.closed"
]) {
  if (!contracts.includes(event)) throw new Error(`누락된 WebSocket 이벤트: ${event}`);
}
console.log("협업 보드의 실행 구조와 검증 명령을 확인했습니다.");
