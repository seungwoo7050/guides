import { randomUUID } from "node:crypto";

import {
  Kysely,
  PostgresDialect,
  sql,
  type Transaction
} from "kysely";
import { Pool, types as pgTypes } from "pg";

import type {
  BoardItem,
  BoardRole,
  BoardSnapshot,
  BoardSummary,
  ItemKind,
  LoginRequest,
  PublicUser,
  SessionUser
} from "@board/contracts";
import type { Database } from "./db-types";
import {
  RepositoryError,
  type AdminAction,
  type AppRepository,
  type BoardEventRecord,
  type CloseBoardResult,
  type MutationResult
} from "./repository";

pgTypes.setTypeParser(20, (value) => {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) {
    throw new Error(`PostgreSQL bigint is outside the JavaScript safe-integer range: ${value}`);
  }
  return parsed;
});

type DbResource = Kysely<Database> | Transaction<Database>;

// [Implementation 5] Serialize each persistent board mutation with a row lock, optimistic item version check, board-version advance, and durable event sequence in one transaction.
export class PostgresRepository implements AppRepository {
  constructor(private readonly db: Kysely<Database>) {}

  async close(): Promise<void> {
    await this.db.destroy();
  }

  async seed(): Promise<void> {
    for (const input of [
      { handle: "owner", displayName: "Board Owner" },
      { handle: "editor", displayName: "Editor" },
      { handle: "viewer", displayName: "Viewer" },
      { handle: "admin", displayName: "Administrator" }
    ]) {
      await this.upsertUser(input);
    }

    const existing = await this.db.selectFrom("boards").select("id").limit(1).executeTakeFirst();
    if (existing) return;

    const owner = await this.requireUserByHandle("owner");
    const editor = await this.requireUserByHandle("editor");
    const viewer = await this.requireUserByHandle("viewer");
    const board = await this.createBoard(owner.id, "Product Discovery");
    await this.inviteMember(board.id, owner.id, editor.handle, "editor");
    await this.inviteMember(board.id, owner.id, viewer.handle, "viewer");
    await this.createItem(board.id, owner.id, {
      kind: "note",
      content: "First hypothesis",
      x: 120,
      y: 100
    });
  }

  async upsertUser(input: LoginRequest): Promise<SessionUser> {
    const row = await this.db.insertInto("users")
      .values({
        handle: input.handle,
        display_name: input.displayName,
        role: input.handle === "admin" ? "admin" : "user",
        status: "active"
      })
      .onConflict((conflict) => conflict.column("handle").doUpdateSet({
        display_name: input.displayName
      }))
      .returning(["id", "handle", "display_name", "role", "status"])
      .executeTakeFirstOrThrow();
    return mapSessionUser(row);
  }

  async createSession(userId: string): Promise<string> {
    const token = randomUUID();
    await this.db.insertInto("sessions").values({
      token,
      user_id: userId,
      expires_at: new Date(Date.now() + 14 * 24 * 60 * 60 * 1_000)
    }).execute();
    return token;
  }

  async getSessionUser(token: string | undefined): Promise<SessionUser | null> {
    if (!token) return null;
    const row = await this.db.selectFrom("sessions")
      .innerJoin("users", "users.id", "sessions.user_id")
      .select([
        "users.id",
        "users.handle",
        "users.display_name",
        "users.role",
        "users.status"
      ])
      .where("sessions.token", "=", token)
      .where("sessions.expires_at", ">", new Date())
      .executeTakeFirst();
    return row ? mapSessionUser(row) : null;
  }

  async deleteSession(token: string | undefined): Promise<void> {
    if (token) await this.db.deleteFrom("sessions").where("token", "=", token).execute();
  }

  async listBoards(userId: string): Promise<BoardSummary[]> {
    const rows = await this.db.selectFrom("board_members")
      .innerJoin("boards", "boards.id", "board_members.board_id")
      .select([
        "boards.id",
        "boards.title",
        "boards.version",
        "boards.closed_at",
        "board_members.role"
      ])
      .where("board_members.user_id", "=", userId)
      .orderBy("boards.title")
      .execute();
    return rows.map((row) => ({
      id: row.id,
      title: row.title,
      role: row.role,
      version: row.version,
      closed: row.closed_at !== null
    }));
  }

  async createBoard(ownerId: string, title: string): Promise<BoardSummary> {
    return this.db.transaction().execute(async (trx) => {
      const board = await trx.insertInto("boards")
        .values({ owner_id: ownerId, title, closed_at: null })
        .returning(["id", "title", "version"])
        .executeTakeFirstOrThrow();
      await trx.insertInto("board_members").values({
        board_id: board.id,
        user_id: ownerId,
        role: "owner"
      }).execute();
      return { id: board.id, title: board.title, role: "owner", version: board.version, closed: false };
    });
  }

  async getBoardSnapshot(boardId: string, userId: string): Promise<BoardSnapshot | null> {
    const membership = await this.db.selectFrom("board_members")
      .innerJoin("boards", "boards.id", "board_members.board_id")
      .select([
        "boards.id",
        "boards.title",
        "boards.version",
        "boards.closed_at",
        "board_members.role"
      ])
      .where("boards.id", "=", boardId)
      .where("board_members.user_id", "=", userId)
      .executeTakeFirst();
    if (!membership) return null;

    const [items, sequenceRow] = await Promise.all([
      this.db.selectFrom("board_items")
        .select(["id", "board_id", "kind", "content", "x", "y", "width", "height", "version"])
        .where("board_id", "=", boardId)
        .orderBy("updated_at")
        .orderBy("id")
        .execute(),
      this.db.selectFrom("board_events")
        .select(sql<number>`coalesce(max(sequence), 0)`.as("sequence"))
        .where("board_id", "=", boardId)
        .executeTakeFirstOrThrow()
    ]);

    return {
      boardId,
      title: membership.title,
      version: membership.version,
      sequence: sequenceRow.sequence,
      closed: membership.closed_at !== null,
      role: membership.role,
      items: items.map(mapBoardItem),
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

  async inviteMember(
    boardId: string,
    actorId: string,
    handle: string,
    role: Exclude<BoardRole, "owner">
  ): Promise<void> {
    await this.db.transaction().execute(async (trx) => {
      await this.assertOwner(trx, boardId, actorId);
      const user = await trx.selectFrom("users").select("id").where("handle", "=", handle).executeTakeFirst();
      if (!user) throw new RepositoryError("user_not_found");
      const existing = await trx.selectFrom("board_members")
        .select("role")
        .where("board_id", "=", boardId)
        .where("user_id", "=", user.id)
        .executeTakeFirst();
      if (existing?.role === "owner") throw new RepositoryError("forbidden");
      await trx.insertInto("board_members")
        .values({ board_id: boardId, user_id: user.id, role })
        .onConflict((conflict) => conflict.columns(["board_id", "user_id"]).doUpdateSet({ role }))
        .execute();
    });
  }

  async changeMemberRole(
    boardId: string,
    actorId: string,
    userId: string,
    role: Exclude<BoardRole, "owner">
  ): Promise<void> {
    await this.db.transaction().execute(async (trx) => {
      await this.assertOwner(trx, boardId, actorId);
      const existing = await trx.selectFrom("board_members")
        .select("role")
        .where("board_id", "=", boardId)
        .where("user_id", "=", userId)
        .executeTakeFirst();
      if (!existing) throw new RepositoryError("member_not_found");
      if (existing.role === "owner") throw new RepositoryError("forbidden");
      const result = await trx.updateTable("board_members")
        .set({ role })
        .where("board_id", "=", boardId)
        .where("user_id", "=", userId)
        .executeTakeFirst();
      if (Number(result.numUpdatedRows) === 0) throw new RepositoryError("member_not_found");
    });
  }

  async listBoardEvents(boardId: string, userId: string): Promise<BoardEventRecord[]> {
    const role = await this.getBoardRole(boardId, userId);
    if (!role) throw new RepositoryError("forbidden");
    const rows = await this.db.selectFrom("board_events")
      .selectAll()
      .where("board_id", "=", boardId)
      .orderBy("sequence", "desc")
      .limit(100)
      .execute();
    return rows.map((row) => ({
      id: row.id,
      boardId: row.board_id,
      sequence: row.sequence,
      actorId: row.actor_id,
      eventType: row.event_type,
      payload: row.payload,
      createdAt: row.created_at.toISOString()
    }));
  }

  async createItem(
    boardId: string,
    actorId: string,
    input: { kind: ItemKind; content: string; x: number; y: number }
  ): Promise<MutationResult> {
    return this.db.transaction().execute(async (trx) => {
      await this.lockWritableBoard(trx, boardId, actorId);
      const row = await trx.insertInto("board_items").values({
        board_id: boardId,
        kind: input.kind,
        content: input.content,
        x: input.x,
        y: input.y,
        updated_by: actorId
      }).returning(["id", "board_id", "kind", "content", "x", "y", "width", "height", "version"])
        .executeTakeFirstOrThrow();
      const event = await this.recordEvent(trx, boardId, actorId, "item.create", mapBoardItem(row));
      return { item: mapBoardItem(row), ...event };
    });
  }

  async updateItem(
    boardId: string,
    actorId: string,
    itemId: string,
    content: string,
    baseVersion: number
  ): Promise<MutationResult | null> {
    return this.db.transaction().execute(async (trx) => {
      await this.lockWritableBoard(trx, boardId, actorId);
      const row = await trx.updateTable("board_items")
        .set({
          content,
          version: sql<number>`version + 1`,
          updated_by: actorId,
          updated_at: new Date()
        })
        .where("id", "=", itemId)
        .where("board_id", "=", boardId)
        .where("version", "=", baseVersion)
        .returning(["id", "board_id", "kind", "content", "x", "y", "width", "height", "version"])
        .executeTakeFirst();
      if (!row) return null;
      const item = mapBoardItem(row);
      const event = await this.recordEvent(trx, boardId, actorId, "item.update", { itemId, content });
      return { item, ...event };
    });
  }

  async persistItemMove(
    boardId: string,
    actorId: string,
    itemId: string,
    x: number,
    y: number,
    baseVersion: number
  ): Promise<MutationResult | null> {
    return this.db.transaction().execute(async (trx) => {
      await this.lockWritableBoard(trx, boardId, actorId);
      const row = await trx.updateTable("board_items")
        .set({
          x,
          y,
          version: sql<number>`version + 1`,
          updated_by: actorId,
          updated_at: new Date()
        })
        .where("id", "=", itemId)
        .where("board_id", "=", boardId)
        .where("version", "=", baseVersion)
        .returning(["id", "board_id", "kind", "content", "x", "y", "width", "height", "version"])
        .executeTakeFirst();
      if (!row) return null;
      const item = mapBoardItem(row);
      const event = await this.recordEvent(trx, boardId, actorId, "item.move", { itemId, x, y });
      return { item, ...event };
    });
  }

  async closeBoard(boardId: string, actorId: string): Promise<CloseBoardResult> {
    return this.db.transaction().execute(async (trx) => {
      await this.assertOwner(trx, boardId, actorId);
      const board = await trx.selectFrom("boards")
        .select(["id", "closed_at"])
        .where("id", "=", boardId)
        .forUpdate()
        .executeTakeFirstOrThrow();
      if (board.closed_at) throw new RepositoryError("board_closed");
      await trx.updateTable("boards").set({ closed_at: new Date() }).where("id", "=", boardId).execute();
      return this.recordEvent(trx, boardId, actorId, "board.closed", { reason: "closed by owner" });
    });
  }

  async listAdminUsers(): Promise<Array<PublicUser & { status: "active" | "suspended" }>> {
    const rows = await this.db.selectFrom("users")
      .select(["id", "handle", "display_name", "status"])
      .orderBy("handle")
      .execute();
    return rows.map((row) => ({
      id: row.id,
      handle: row.handle,
      displayName: row.display_name,
      status: row.status
    }));
  }

  async listAdminActions(): Promise<AdminAction[]> {
    const rows = await this.db.selectFrom("admin_actions")
      .selectAll()
      .orderBy("created_at", "desc")
      .limit(100)
      .execute();
    return rows.map((row) => ({
      id: row.id,
      actorId: row.actor_id,
      targetUserId: row.target_user_id,
      action: row.action,
      reason: row.reason,
      createdAt: row.created_at.toISOString()
    }));
  }

  async setUserStatus(
    actorId: string,
    targetUserId: string,
    status: "active" | "suspended",
    reason: string
  ): Promise<void> {
    await this.db.transaction().execute(async (trx) => {
      const result = await trx.updateTable("users").set({ status }).where("id", "=", targetUserId).executeTakeFirst();
      if (Number(result.numUpdatedRows) === 0) throw new RepositoryError("user_not_found");
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

  private async requireUserByHandle(handle: string): Promise<SessionUser> {
    const row = await this.db.selectFrom("users")
      .select(["id", "handle", "display_name", "role", "status"])
      .where("handle", "=", handle)
      .executeTakeFirstOrThrow();
    return mapSessionUser(row);
  }

  private async assertOwner(resource: DbResource, boardId: string, actorId: string): Promise<void> {
    const member = await resource.selectFrom("board_members")
      .select("role")
      .where("board_id", "=", boardId)
      .where("user_id", "=", actorId)
      .executeTakeFirst();
    if (member?.role !== "owner") throw new RepositoryError("forbidden");
  }

  private async lockWritableBoard(trx: Transaction<Database>, boardId: string, actorId: string): Promise<void> {
    const board = await trx.selectFrom("boards")
      .select(["id", "closed_at"])
      .where("id", "=", boardId)
      .forUpdate()
      .executeTakeFirst();
    if (!board || board.closed_at) throw new RepositoryError("board_closed");
    const member = await trx.selectFrom("board_members")
      .select("role")
      .where("board_id", "=", boardId)
      .where("user_id", "=", actorId)
      .executeTakeFirst();
    if (member?.role !== "owner" && member?.role !== "editor") {
      throw new RepositoryError("read_only");
    }
  }

  private async recordEvent(
    trx: Transaction<Database>,
    boardId: string,
    actorId: string,
    eventType: string,
    payload: unknown
  ): Promise<{ sequence: number; boardVersion: number }> {
    const sequenceRow = await trx.selectFrom("board_events")
      .select(sql<number>`coalesce(max(sequence), 0) + 1`.as("sequence"))
      .where("board_id", "=", boardId)
      .executeTakeFirstOrThrow();
    const board = await trx.updateTable("boards")
      .set({ version: sql<number>`version + 1` })
      .where("id", "=", boardId)
      .returning("version")
      .executeTakeFirstOrThrow();
    await trx.insertInto("board_events").values({
      board_id: boardId,
      sequence: sequenceRow.sequence,
      actor_id: actorId,
      event_type: eventType,
      payload
    }).execute();
    return { sequence: sequenceRow.sequence, boardVersion: board.version };
  }
}

export function createPostgresRepository(connectionString: string): AppRepository {
  const pool = new Pool({ connectionString, max: 10 });
  const db = new Kysely<Database>({ dialect: new PostgresDialect({ pool }) });
  return new PostgresRepository(db);
}

function mapSessionUser(row: {
  id: string;
  handle: string;
  display_name: string;
  role: "user" | "admin";
  status: "active" | "suspended";
}): SessionUser {
  return {
    id: row.id,
    handle: row.handle,
    displayName: row.display_name,
    role: row.role,
    status: row.status
  };
}

function mapBoardItem(row: {
  id: string;
  board_id: string;
  kind: "note" | "shape";
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  version: number;
}): BoardItem {
  return {
    id: row.id,
    boardId: row.board_id,
    kind: row.kind,
    content: row.content,
    x: row.x,
    y: row.y,
    width: row.width,
    height: row.height,
    version: row.version
  };
}
