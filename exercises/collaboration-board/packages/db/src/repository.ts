import { randomUUID } from "node:crypto";

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
import { DEFAULT_ITEM_HEIGHT, DEFAULT_ITEM_WIDTH } from "@board/contracts";

export type RepositoryErrorCode =
  | "forbidden"
  | "read_only"
  | "user_not_found"
  | "member_not_found"
  | "board_closed";

export class RepositoryError extends Error {
  constructor(readonly code: RepositoryErrorCode) {
    super(code);
  }
}

export interface BoardEventRecord {
  id: string;
  boardId: string;
  sequence: number;
  actorId: string;
  eventType: string;
  payload: unknown;
  createdAt: string;
}

export interface AdminAction {
  id: string;
  actorId: string;
  targetUserId: string;
  action: "suspend" | "restore";
  reason: string;
  createdAt: string;
}

export interface MutationResult {
  item: BoardItem;
  sequence: number;
  boardVersion: number;
}

export interface CloseBoardResult {
  sequence: number;
  boardVersion: number;
}

export interface AppRepository {
  close(): Promise<void>;
  seed(): Promise<void>;
  upsertUser(input: LoginRequest): Promise<SessionUser>;
  createSession(userId: string): Promise<string>;
  getSessionUser(token: string | undefined): Promise<SessionUser | null>;
  deleteSession(token: string | undefined): Promise<void>;
  listBoards(userId: string): Promise<BoardSummary[]>;
  createBoard(ownerId: string, title: string): Promise<BoardSummary>;
  getBoardSnapshot(boardId: string, userId: string): Promise<BoardSnapshot | null>;
  getBoardRole(boardId: string, userId: string): Promise<BoardRole | null>;
  inviteMember(boardId: string, actorId: string, handle: string, role: Exclude<BoardRole, "owner">): Promise<void>;
  changeMemberRole(boardId: string, actorId: string, userId: string, role: Exclude<BoardRole, "owner">): Promise<void>;
  listBoardEvents(boardId: string, userId: string): Promise<BoardEventRecord[]>;
  createItem(boardId: string, actorId: string, input: { kind: ItemKind; content: string; x: number; y: number }): Promise<MutationResult>;
  updateItem(boardId: string, actorId: string, itemId: string, content: string, baseVersion: number): Promise<MutationResult | null>;
  persistItemMove(boardId: string, actorId: string, itemId: string, x: number, y: number, baseVersion: number): Promise<MutationResult | null>;
  closeBoard(boardId: string, actorId: string): Promise<CloseBoardResult>;
  listAdminUsers(): Promise<Array<PublicUser & { status: "active" | "suspended" }>>;
  listAdminActions(): Promise<AdminAction[]>;
  setUserStatus(actorId: string, targetUserId: string, status: "active" | "suspended", reason: string): Promise<void>;
}

type StoredBoard = { id: string; ownerId: string; title: string; version: number; closed: boolean };

// [Implementation 4] Define persistence as an application port and provide an app-owned memory adapter that preserves the same membership, version, sequence, and revocation rules.
export class MemoryRepository implements AppRepository {
  private readonly users = new Map<string, SessionUser>();
  private readonly sessions = new Map<string, { userId: string; expiresAt: number }>();
  private readonly boards = new Map<string, StoredBoard>();
  private readonly members = new Map<string, Map<string, BoardRole>>();
  private readonly items = new Map<string, Map<string, BoardItem>>();
  private readonly events = new Map<string, BoardEventRecord[]>();
  private readonly actions: AdminAction[] = [];

  async close(): Promise<void> {}

  async seed(): Promise<void> {
    for (const input of [
      { handle: "owner", displayName: "Board Owner" },
      { handle: "editor", displayName: "Editor" },
      { handle: "viewer", displayName: "Viewer" },
      { handle: "admin", displayName: "Administrator" }
    ]) {
      await this.upsertUser(input);
    }

    if (this.boards.size > 0) return;
    const owner = this.userByHandle("owner")!;
    const editor = this.userByHandle("editor")!;
    const viewer = this.userByHandle("viewer")!;
    const board = await this.createBoard(owner.id, "Product Discovery");
    this.members.get(board.id)!.set(editor.id, "editor");
    this.members.get(board.id)!.set(viewer.id, "viewer");
    await this.createItem(board.id, owner.id, {
      kind: "note",
      content: "First hypothesis",
      x: 120,
      y: 100
    });
  }

  async upsertUser(input: LoginRequest): Promise<SessionUser> {
    const existing = this.userByHandle(input.handle);
    if (existing) {
      const updated = { ...existing, displayName: input.displayName };
      this.users.set(existing.id, updated);
      return { ...updated };
    }

    const user: SessionUser = {
      id: randomUUID(),
      ...input,
      role: input.handle === "admin" ? "admin" : "user",
      status: "active"
    };
    this.users.set(user.id, user);
    return { ...user };
  }

  async createSession(userId: string): Promise<string> {
    const token = randomUUID();
    this.sessions.set(token, { userId, expiresAt: Date.now() + 14 * 24 * 60 * 60 * 1_000 });
    return token;
  }

  async getSessionUser(token: string | undefined): Promise<SessionUser | null> {
    const session = token ? this.sessions.get(token) : undefined;
    if (!session || session.expiresAt <= Date.now()) {
      if (token) this.sessions.delete(token);
      return null;
    }
    const user = this.users.get(session.userId);
    return user ? { ...user } : null;
  }

  async deleteSession(token: string | undefined): Promise<void> {
    if (token) this.sessions.delete(token);
  }

  async listBoards(userId: string): Promise<BoardSummary[]> {
    const result: BoardSummary[] = [];
    for (const board of this.boards.values()) {
      const role = this.members.get(board.id)?.get(userId);
      if (role) result.push({ id: board.id, title: board.title, role, version: board.version, closed: board.closed });
    }
    return result.sort((left, right) => left.title.localeCompare(right.title));
  }

  async createBoard(ownerId: string, title: string): Promise<BoardSummary> {
    const board: StoredBoard = { id: randomUUID(), ownerId, title, version: 0, closed: false };
    this.boards.set(board.id, board);
    this.members.set(board.id, new Map([[ownerId, "owner"]]));
    this.items.set(board.id, new Map());
    this.events.set(board.id, []);
    return { id: board.id, title, role: "owner", version: 0, closed: false };
  }

  async getBoardSnapshot(boardId: string, userId: string): Promise<BoardSnapshot | null> {
    const board = this.boards.get(boardId);
    const role = this.members.get(boardId)?.get(userId);
    if (!board || !role) return null;
    const events = this.events.get(boardId) ?? [];
    return {
      boardId,
      title: board.title,
      version: board.version,
      sequence: events.at(-1)?.sequence ?? 0,
      closed: board.closed,
      role,
      items: [...(this.items.get(boardId)?.values() ?? [])].map((item) => ({ ...item })),
      serverTime: new Date().toISOString()
    };
  }

  async getBoardRole(boardId: string, userId: string): Promise<BoardRole | null> {
    return this.members.get(boardId)?.get(userId) ?? null;
  }

  async inviteMember(boardId: string, actorId: string, handle: string, role: Exclude<BoardRole, "owner">): Promise<void> {
    this.assertOwner(boardId, actorId);
    const user = this.userByHandle(handle);
    if (!user) throw new RepositoryError("user_not_found");
    const memberships = this.members.get(boardId)!;
    if (memberships.get(user.id) === "owner") throw new RepositoryError("forbidden");
    memberships.set(user.id, role);
  }

  async changeMemberRole(boardId: string, actorId: string, userId: string, role: Exclude<BoardRole, "owner">): Promise<void> {
    this.assertOwner(boardId, actorId);
    const memberships = this.members.get(boardId);
    const currentRole = memberships?.get(userId);
    if (!currentRole) throw new RepositoryError("member_not_found");
    if (currentRole === "owner") throw new RepositoryError("forbidden");
    memberships!.set(userId, role);
  }

  async listBoardEvents(boardId: string, userId: string): Promise<BoardEventRecord[]> {
    if (!this.members.get(boardId)?.has(userId)) throw new RepositoryError("forbidden");
    return [...(this.events.get(boardId) ?? [])]
      .reverse()
      .map((event) => ({ ...event, payload: structuredClone(event.payload) }));
  }

  async createItem(
    boardId: string,
    actorId: string,
    input: { kind: ItemKind; content: string; x: number; y: number }
  ): Promise<MutationResult> {
    this.assertWritable(boardId, actorId);
    const item: BoardItem = {
      id: randomUUID(),
      boardId,
      ...input,
      width: DEFAULT_ITEM_WIDTH,
      height: DEFAULT_ITEM_HEIGHT,
      version: 1
    };
    this.items.get(boardId)!.set(item.id, item);
    return this.record(boardId, actorId, "item.create", item, item);
  }

  async updateItem(
    boardId: string,
    actorId: string,
    itemId: string,
    content: string,
    baseVersion: number
  ): Promise<MutationResult | null> {
    this.assertWritable(boardId, actorId);
    const item = this.items.get(boardId)?.get(itemId);
    if (!item || item.version !== baseVersion) return null;
    item.content = content;
    item.version += 1;
    return this.record(boardId, actorId, "item.update", { itemId, content }, item);
  }

  async persistItemMove(
    boardId: string,
    actorId: string,
    itemId: string,
    x: number,
    y: number,
    baseVersion: number
  ): Promise<MutationResult | null> {
    this.assertWritable(boardId, actorId);
    const item = this.items.get(boardId)?.get(itemId);
    if (!item || item.version !== baseVersion) return null;
    item.x = x;
    item.y = y;
    item.version += 1;
    return this.record(boardId, actorId, "item.move", { itemId, x, y }, item);
  }

  async closeBoard(boardId: string, actorId: string): Promise<CloseBoardResult> {
    this.assertOwner(boardId, actorId);
    const board = this.boards.get(boardId)!;
    if (board.closed) throw new RepositoryError("board_closed");
    board.closed = true;
    const recorded = this.recordEvent(boardId, actorId, "board.closed", { reason: "closed by owner" });
    return { sequence: recorded.sequence, boardVersion: recorded.boardVersion };
  }

  async listAdminUsers(): Promise<Array<PublicUser & { status: "active" | "suspended" }>> {
    return [...this.users.values()].map(({ role: _role, ...user }) => ({ ...user }));
  }

  async listAdminActions(): Promise<AdminAction[]> {
    return [...this.actions].reverse().map((action) => ({ ...action }));
  }

  async setUserStatus(
    actorId: string,
    targetUserId: string,
    status: "active" | "suspended",
    reason: string
  ): Promise<void> {
    const target = this.users.get(targetUserId);
    if (!target) throw new RepositoryError("user_not_found");
    this.users.set(targetUserId, { ...target, status });
    this.actions.push({
      id: randomUUID(),
      actorId,
      targetUserId,
      action: status === "suspended" ? "suspend" : "restore",
      reason,
      createdAt: new Date().toISOString()
    });
    if (status === "suspended") {
      for (const [token, session] of this.sessions) {
        if (session.userId === targetUserId) this.sessions.delete(token);
      }
    }
  }

  private userByHandle(handle: string): SessionUser | null {
    return [...this.users.values()].find((user) => user.handle === handle) ?? null;
  }

  private record(
    boardId: string,
    actorId: string,
    eventType: string,
    payload: unknown,
    item: BoardItem
  ): MutationResult {
    const event = this.recordEvent(boardId, actorId, eventType, payload);
    return { item: { ...item }, sequence: event.sequence, boardVersion: event.boardVersion };
  }

  private recordEvent(boardId: string, actorId: string, eventType: string, payload: unknown) {
    const board = this.boards.get(boardId)!;
    const events = this.events.get(boardId)!;
    board.version += 1;
    const event: BoardEventRecord = {
      id: randomUUID(),
      boardId,
      sequence: (events.at(-1)?.sequence ?? 0) + 1,
      actorId,
      eventType,
      payload: structuredClone(payload),
      createdAt: new Date().toISOString()
    };
    events.push(event);
    return { sequence: event.sequence, boardVersion: board.version };
  }

  private assertOwner(boardId: string, actorId: string): void {
    if (this.members.get(boardId)?.get(actorId) !== "owner") throw new RepositoryError("forbidden");
  }

  private assertWritable(boardId: string, actorId: string): void {
    const board = this.boards.get(boardId);
    if (!board || board.closed) throw new RepositoryError("board_closed");
    const role = this.members.get(boardId)?.get(actorId);
    if (role !== "owner" && role !== "editor") throw new RepositoryError("read_only");
  }
}

export function createMemoryRepository(): AppRepository {
  return new MemoryRepository();
}
