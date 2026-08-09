import { createRequire } from "node:module";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const requireFromDatabasePackage = createRequire(
  new URL("../../../projects/collaboration-board/packages/db/package.json", import.meta.url)
);
const { Client } = requireFromDatabasePackage("pg") as typeof import("pg");
const workRoot = process.env.LEARNER_WORK_ROOT;
const databaseUrl = process.env.DATABASE_URL;
if (!workRoot || !databaseUrl) throw new Error("LEARNER_WORK_ROOT와 DATABASE_URL이 필요합니다.");

const client = new Client({ connectionString: databaseUrl });
let ownerId = "";
let boardId = "";

type ItemMutation = {
  item: { id: string; version: number };
  sequence: number;
  boardVersion: number;
};
type Stage5Repository = {
  close(): Promise<void>;
  upsertUser(input: { handle: string; displayName: string }): Promise<{ id: string }>;
  createBoard(ownerId: string, title: string): Promise<{ id: string }>;
  createItem(
    boardId: string,
    actorId: string,
    input: { kind: "note"; content: string; x: number; y: number }
  ): Promise<ItemMutation>;
  updateItem(
    boardId: string,
    actorId: string,
    itemId: string,
    content: string,
    baseVersion: number
  ): Promise<ItemMutation | null>;
  persistItemMove(
    boardId: string,
    actorId: string,
    itemId: string,
    x: number,
    y: number,
    baseVersion: number
  ): Promise<ItemMutation | null>;
};

beforeAll(async () => {
  await client.connect();
  const migrations = path.join(workRoot, "packages", "db", "migrations");
  const files = (await readdir(migrations)).filter((name) => name.endsWith(".sql")).sort();
  if (files.length === 0) throw new Error("적용할 PostgreSQL migration이 없습니다.");
  const migrationSql = await Promise.all(files.map((file) => readFile(path.join(migrations, file), "utf8")));
  for (let pass = 0; pass < 2; pass += 1) {
    for (const source of migrationSql) await client.query(source);
  }
});

afterAll(async () => {
  await client.end();
});

describe("저장소 소유 Stage 5 PostgreSQL oracle", () => {
  it("필수 협업 보드 schema를 migration으로 만듭니다", async () => {
    const result = await client.query<{ table_name: string }>(`
      select table_name
      from information_schema.tables
      where table_schema = 'public'
    `);
    const tables = new Set(result.rows.map((row) => row.table_name));
    for (const table of [
      "users", "sessions", "boards", "board_members",
      "board_items", "board_events", "admin_actions"
    ]) expect(tables.has(table), `${table} table 누락`).toBe(true);
  });

  it("외래 키·역할 check·event sequence unique 제약을 강제합니다", async () => {
    const owner = await client.query<{ id: string }>(
      "insert into users(handle, display_name) values ($1, $2) returning id",
      ["oracle-owner", "Oracle Owner"]
    );
    ownerId = owner.rows[0].id;
    const member = await client.query<{ id: string }>(
      "insert into users(handle, display_name) values ($1, $2) returning id",
      ["oracle-member", "Oracle Member"]
    );
    await expect(client.query(
      "insert into sessions(token, user_id, expires_at) values ($1, gen_random_uuid(), now() + interval '1 hour')",
      ["invalid-session"]
    )).rejects.toMatchObject({ code: "23503" });

    const board = await client.query<{ id: string }>(
      "insert into boards(owner_id, title) values ($1, $2) returning id",
      [ownerId, "Oracle Board"]
    );
    boardId = board.rows[0].id;
    await client.query(
      "insert into board_members(board_id, user_id, role) values ($1, $2, 'owner')",
      [boardId, ownerId]
    );
    await expect(client.query(
      "insert into board_members(board_id, user_id, role) values ($1, $2, 'writer')",
      [boardId, member.rows[0].id]
    )).rejects.toMatchObject({ code: "23514" });

    await client.query(
      "insert into board_events(board_id, sequence, actor_id, event_type, payload) values ($1, 1, $2, 'oracle', '{}'::jsonb)",
      [boardId, ownerId]
    );
    await expect(client.query(
      "insert into board_events(board_id, sequence, actor_id, event_type, payload) values ($1, 1, $2, 'duplicate', '{}'::jsonb)",
      [boardId, ownerId]
    )).rejects.toMatchObject({ code: "23505" });
    await client.query("delete from board_events where board_id = $1", [boardId]);
  });

  it("item·board version·activity event를 함께 rollback하고 commit할 수 있습니다", async () => {
    const item = await client.query<{ id: string }>(`
      insert into board_items(board_id, kind, content, x, y, updated_by)
      values ($1, 'note', 'before', 10, 20, $2)
      returning id
    `, [boardId, ownerId]);
    const itemId = item.rows[0].id;

    await client.query("begin");
    await client.query("update board_items set content = 'rolled-back', version = version + 1 where id = $1", [itemId]);
    await client.query("update boards set version = version + 1 where id = $1", [boardId]);
    await client.query(
      "insert into board_events(board_id, sequence, actor_id, event_type, payload) values ($1, 1, $2, 'item.update', '{}'::jsonb)",
      [boardId, ownerId]
    );
    await client.query("rollback");
    expect((await client.query("select content, version from board_items where id = $1", [itemId])).rows[0]).toMatchObject({ content: "before", version: 0 });
    expect((await client.query("select version from boards where id = $1", [boardId])).rows[0].version).toBe(0);
    expect(Number((await client.query("select count(*) from board_events where board_id = $1", [boardId])).rows[0].count)).toBe(0);

    await client.query("begin");
    await client.query("update board_items set content = 'committed', version = version + 1 where id = $1", [itemId]);
    await client.query("update boards set version = version + 1 where id = $1", [boardId]);
    await client.query(
      "insert into board_events(board_id, sequence, actor_id, event_type, payload) values ($1, 1, $2, 'item.update', '{}'::jsonb)",
      [boardId, ownerId]
    );
    await client.query("commit");
    expect((await client.query("select content, version from board_items where id = $1", [itemId])).rows[0]).toMatchObject({ content: "committed", version: 1 });
    expect((await client.query("select version from boards where id = $1", [boardId])).rows[0].version).toBe(1);
    expect(Number((await client.query("select count(*) from board_events where board_id = $1", [boardId])).rows[0].count)).toBe(1);
  });

  it("PostgreSQL repository가 세 영속 변경을 transaction 경계에 둡니다", async () => {
    const source = await readFile(path.join(workRoot, "packages", "db", "src", "postgres.ts"), "utf8");
    expect(source).toMatch(/\.transaction\s*\(\s*\)\s*\.execute\s*\(/);
    for (const table of ["board_items", "boards", "board_events"]) expect(source).toContain(table);
  });

  it("같은 baseVersion의 update와 move 중 하나만 commit합니다", async () => {
    const repository = await createLearnerRepository();
    try {
      const owner = await repository.upsertUser({
        handle: "oracle-concurrency-owner",
        displayName: "Concurrency Owner"
      });
      const board = await repository.createBoard(owner.id, "Concurrency Oracle Board");
      const created = await repository.createItem(board.id, owner.id, {
        kind: "note",
        content: "before race",
        x: 10,
        y: 20
      });
      const eventCountBefore = Number((await client.query(
        "select count(*) from board_events where board_id = $1",
        [board.id]
      )).rows[0].count);

      const [updated, moved] = await Promise.all([
        repository.updateItem(board.id, owner.id, created.item.id, "won by update", created.item.version),
        repository.persistItemMove(board.id, owner.id, created.item.id, 90, 80, created.item.version)
      ]);
      expect([updated, moved].filter((result) => result !== null)).toHaveLength(1);

      const itemState = (await client.query<{ version: number }>(
        "select version from board_items where id = $1",
        [created.item.id]
      )).rows[0];
      const boardState = (await client.query<{ version: number }>(
        "select version from boards where id = $1",
        [board.id]
      )).rows[0];
      const eventCountAfter = Number((await client.query(
        "select count(*) from board_events where board_id = $1",
        [board.id]
      )).rows[0].count);
      expect(itemState.version).toBe(created.item.version + 1);
      expect(boardState.version).toBe(created.boardVersion + 1);
      expect(eventCountAfter).toBe(eventCountBefore + 1);
    } finally {
      await repository.close();
    }
  });

  it("repository event 실패 시 item·board·event 쓰기를 실제로 모두 rollback합니다", async () => {
    const repository = await createLearnerRepository();
    let triggerInstalled = false;
    try {
      const owner = await repository.upsertUser({ handle: "oracle-transaction-owner", displayName: "Transaction Owner" });
      const board = await repository.createBoard(owner.id, "Transaction Oracle Board");
      await client.query(`
        create or replace function reject_oracle_board_event() returns trigger
        language plpgsql as $$ begin raise exception 'oracle board event failure'; end $$
      `);
      await client.query(`
        create trigger reject_oracle_board_event_trigger
        before insert on board_events
        for each row execute function reject_oracle_board_event()
      `);
      triggerInstalled = true;

      await expect(repository.createItem(board.id, owner.id, {
        kind: "note",
        content: "must rollback",
        x: 10,
        y: 20
      })).rejects.toThrow();
      expect(Number((await client.query("select count(*) from board_items where board_id = $1", [board.id])).rows[0].count)).toBe(0);
      expect((await client.query("select version from boards where id = $1", [board.id])).rows[0].version).toBe(0);
      expect(Number((await client.query("select count(*) from board_events where board_id = $1", [board.id])).rows[0].count)).toBe(0);
    } finally {
      if (triggerInstalled) await client.query("drop trigger if exists reject_oracle_board_event_trigger on board_events");
      await client.query("drop function if exists reject_oracle_board_event()");
      await repository.close();
    }
  });
});

async function createLearnerRepository() {
  const moduleUrl = pathToFileURL(path.join(workRoot, "packages", "db", "src", "postgres.ts")).href;
  const repositoryModule = await import(/* @vite-ignore */ moduleUrl) as {
    createPostgresRepository?: (url: string) => Stage5Repository;
  };
  expect(repositoryModule.createPostgresRepository).toBeTypeOf("function");
  return repositoryModule.createPostgresRepository!(databaseUrl);
}
