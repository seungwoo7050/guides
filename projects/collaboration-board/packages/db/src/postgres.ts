import { randomUUID } from "node:crypto";
import { Kysely, PostgresDialect, sql, type Transaction } from "kysely";
import { Pool } from "pg";
import type {
  BoardItem,
  BoardRole,
  BoardSnapshot,
  BoardSummary,
  LoginRequest,
  PublicUser,
  SessionUser
} from "@board/contracts";
import type { AdminAction, AppRepository, BoardEventRecord } from "./index";
import type { Database } from "./db-types";

export function createPostgresRepository(url: string): AppRepository {
  const pool = new Pool({ connectionString: url });
  const db = new Kysely<Database>({ dialect: new PostgresDialect({ pool }) });
  return new PostgresRepository(db, pool);
}

class PostgresRepository implements AppRepository {
  constructor(private readonly db: Kysely<Database>, private readonly pool: Pool) {}

  async close() {
    await this.db.destroy();
    await this.pool.end().catch(() => undefined);
  }
  async seed() {
    for (const input of [
      { handle: "owner", displayName: "보드 소유자" },
      { handle: "editor", displayName: "편집자" },
      { handle: "viewer", displayName: "읽기 전용 사용자" },
      { handle: "admin", displayName: "운영자" }
    ]) await this.upsertUser(input);
    await this.db.updateTable("users").set({ role: "admin" }).where("handle", "=", "admin").execute();
  }
  async upsertUser(input: LoginRequest) {
    const row = await this.db.insertInto("users")
      .values({ handle: input.handle, display_name: input.displayName })
      .onConflict((conflict) => conflict.column("handle").doUpdateSet({ display_name: input.displayName }))
      .returningAll()
      .executeTakeFirstOrThrow();
    return sessionUser(row);
  }
  async createSession(userId: string) {
    const token = randomUUID();
    await this.db.insertInto("sessions").values({
      token,
      user_id: userId,
      expires_at: new Date(Date.now() + 14 * 24 * 60 * 60 * 1_000)
    }).execute();
    return token;
  }
  async getSessionUser(token: string | undefined) {
    if (!token) return null;
    const row = await this.db.selectFrom("sessions as s")
      .innerJoin("users as u", "u.id", "s.user_id")
      .select(["u.id", "u.handle", "u.display_name", "u.role", "u.status"])
      .where("s.token", "=", token)
      .where("s.expires_at", ">", new Date())
      .executeTakeFirst();
    return row ? sessionUser(row) : null;
  }
  async deleteSession(token: string | undefined) {
    if (token) await this.db.deleteFrom("sessions").where("token", "=", token).execute();
  }
  async listBoards(userId: string): Promise<BoardSummary[]> {
    const rows = await this.db.selectFrom("board_members as m")
      .innerJoin("boards as b", "b.id", "m.board_id")
      .select(["b.id", "b.title", "b.version", "b.closed_at", "m.role"])
      .where("m.user_id", "=", userId)
      .orderBy("b.created_at", "desc")
      .execute();
    return rows.map((row) => ({
      id: row.id,
      title: row.title,
      role: row.role,
      version: row.version,
      closed: row.closed_at !== null
    }));
  }
  async createBoard(ownerId: string, title: string) {
    return this.db.transaction().execute(async (trx) => {
      const board = await trx.insertInto("boards")
        .values({ owner_id: ownerId, title, closed_at: null })
        .returningAll()
        .executeTakeFirstOrThrow();
      await trx.insertInto("board_members")
        .values({ board_id: board.id, user_id: ownerId, role: "owner" })
        .execute();
      return { id: board.id, title, role: "owner" as const, version: board.version, closed: false };
    });
  }
  async getBoardSnapshot(boardId: string, userId: string): Promise<BoardSnapshot | null> {
    const board = await this.db.selectFrom("boards as b")
      .innerJoin("board_members as m", "m.board_id", "b.id")
      .select(["b.id", "b.title", "b.version", "b.closed_at", "m.role"])
      .where("b.id", "=", boardId)
      .where("m.user_id", "=", userId)
      .executeTakeFirst();
    if (!board) return null;
    const items = await this.db.selectFrom("board_items").selectAll().where("board_id", "=", boardId).execute();
    const latest = await this.db.selectFrom("board_events")
      .select(({ fn }) => fn.max<number>("sequence").as("sequence"))
      .where("board_id", "=", boardId)
      .executeTakeFirst();
    return {
      boardId,
      title: board.title,
      version: board.version,
      sequence: Number(latest?.sequence ?? 0),
      closed: board.closed_at !== null,
      role: board.role,
      items: items.map(boardItem),
      serverTime: new Date().toISOString()
    };
  }
  async getBoardRole(boardId: string, userId: string): Promise<BoardRole | null> {
    const row = await this.db.selectFrom("board_members")
      .select("role")
      .where("board_id", "=", boardId)
      .where("user_id", "=", userId)
      .executeTakeFirst();
    return row?.role ?? null;
  }
  async inviteMember(boardId: string, actorId: string, handle: string, role: Exclude<BoardRole, "owner">) {
    await this.assertOwner(boardId, actorId);
    const user = await this.db.selectFrom("users").select("id").where("handle", "=", handle).executeTakeFirstOrThrow();
    await this.db.insertInto("board_members")
      .values({ board_id: boardId, user_id: user.id, role })
      .onConflict((conflict) => conflict.columns(["board_id", "user_id"]).doUpdateSet({ role }))
      .execute();
  }
  async changeMemberRole(boardId: string, actorId: string, userId: string, role: Exclude<BoardRole, "owner">) {
    await this.assertOwner(boardId, actorId);
    const result = await this.db.updateTable("board_members")
      .set({ role })
      .where("board_id", "=", boardId)
      .where("user_id", "=", userId)
      .where("role", "!=", "owner")
      .executeTakeFirst();
    if (Number(result.numUpdatedRows) !== 1) throw new Error("member_not_found");
  }
  async listBoardEvents(boardId: string, userId: string): Promise<BoardEventRecord[]> {
    if (!await this.getBoardRole(boardId, userId)) throw new Error("forbidden");
    const rows = await this.db.selectFrom("board_events")
      .selectAll()
      .where("board_id", "=", boardId)
      .orderBy("sequence", "desc")
      .limit(100)
      .execute();
    return rows.map((row) => ({
      id: row.id,
      boardId: row.board_id,
      sequence: Number(row.sequence),
      actorId: row.actor_id,
      eventType: row.event_type,
      payload: row.payload,
      createdAt: row.created_at.toISOString()
    }));
  }
  async createItem(boardId: string, actorId: string, input: Pick<BoardItem, "kind" | "content" | "x" | "y">) {
    await this.assertWritable(boardId, actorId);
    return this.db.transaction().execute(async (trx) => {
      const item = await trx.insertInto("board_items").values({
        board_id: boardId,
        kind: input.kind,
        content: input.content,
        x: input.x,
        y: input.y,
        width: 240,
        height: 140,
        version: 1,
        updated_by: actorId
      }).returningAll().executeTakeFirstOrThrow();
      return this.record(trx, boardId, actorId, "item.create", boardItem(item), boardItem(item));
    });
  }
  async updateItem(boardId: string, actorId: string, itemId: string, content: string, baseVersion: number) {
    await this.assertWritable(boardId, actorId);
    return this.db.transaction().execute(async (trx) => {
      const row = await trx.updateTable("board_items")
        .set({ content, version: baseVersion + 1, updated_by: actorId, updated_at: new Date() })
        .where("id", "=", itemId)
        .where("board_id", "=", boardId)
        .where("version", "=", baseVersion)
        .returningAll()
        .executeTakeFirst();
      if (!row) return null;
      return this.record(trx, boardId, actorId, "item.update", { itemId, content }, boardItem(row));
    });
  }
  async persistItemMove(boardId: string, actorId: string, itemId: string, x: number, y: number, baseVersion: number) {
    await this.assertWritable(boardId, actorId);
    return this.db.transaction().execute(async (trx) => {
      const row = await trx.updateTable("board_items")
        .set({ x, y, version: baseVersion + 1, updated_by: actorId, updated_at: new Date() })
        .where("id", "=", itemId)
        .where("board_id", "=", boardId)
        .where("version", "=", baseVersion)
        .returningAll()
        .executeTakeFirst();
      if (!row) return null;
      return this.record(trx, boardId, actorId, "item.move", { itemId, x, y }, boardItem(row));
    });
  }
  async listAdminUsers() {
    const rows = await this.db.selectFrom("users").selectAll().orderBy("created_at", "desc").execute();
    return rows.map((row) => ({ ...publicUser(row), status: row.status }));
  }
  async listAdminActions(): Promise<AdminAction[]> {
    const rows = await this.db.selectFrom("admin_actions").selectAll().orderBy("created_at", "desc").execute();
    return rows.map((row) => ({
      id: row.id,
      actorId: row.actor_id,
      targetUserId: row.target_user_id,
      action: row.action,
      reason: row.reason,
      createdAt: row.created_at.toISOString()
    }));
  }
  async setUserStatus(actorId: string, targetUserId: string, status: "active" | "suspended", reason: string) {
    await this.db.transaction().execute(async (trx) => {
      await trx.updateTable("users").set({ status }).where("id", "=", targetUserId).executeTakeFirstOrThrow();
      await trx.insertInto("admin_actions").values({
        actor_id: actorId,
        target_user_id: targetUserId,
        action: status === "suspended" ? "suspend" : "restore",
        reason
      }).execute();
      if (status === "suspended") {
        await trx.deleteFrom("sessions").where("user_id", "=", targetUserId).execute();
      }
    });
  }

  private async assertOwner(boardId: string, actorId: string) {
    if (await this.getBoardRole(boardId, actorId) !== "owner") throw new Error("forbidden");
  }
  private async assertWritable(boardId: string, actorId: string) {
    const role = await this.getBoardRole(boardId, actorId);
    if (role !== "owner" && role !== "editor") throw new Error("read_only");
  }
  private async record(
    trx: Transaction<Database>,
    boardId: string,
    actorId: string,
    eventType: string,
    payload: unknown,
    item: BoardItem
  ) {
    const board = await trx.updateTable("boards")
      .set(({ eb }) => ({ version: eb("version", "+", 1) }))
      .where("id", "=", boardId)
      .returning("version")
      .executeTakeFirstOrThrow();
    const latest = await trx.selectFrom("board_events")
      .select(({ fn }) => fn.max<number>("sequence").as("sequence"))
      .where("board_id", "=", boardId)
      .executeTakeFirst();
    const sequence = Number(latest?.sequence ?? 0) + 1;
    await trx.insertInto("board_events").values({
      board_id: boardId,
      sequence,
      actor_id: actorId,
      event_type: eventType,
      payload
    }).execute();
    return { item, sequence, boardVersion: board.version };
  }
}

type UserRow = {
  id: string;
  handle: string;
  display_name: string;
  role: "user" | "admin";
  status: "active" | "suspended";
};
type ItemRow = {
  id: string;
  board_id: string;
  kind: "note" | "shape";
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  version: number;
};
function publicUser(row: UserRow): PublicUser {
  return { id: row.id, handle: row.handle, displayName: row.display_name };
}
function sessionUser(row: UserRow): SessionUser {
  return { ...publicUser(row), role: row.role, status: row.status };
}
function boardItem(row: ItemRow): BoardItem {
  return {
    id: row.id,
    boardId: row.board_id,
    kind: row.kind,
    content: row.content,
    x: Number(row.x),
    y: Number(row.y),
    width: Number(row.width),
    height: Number(row.height),
    version: row.version
  };
}
