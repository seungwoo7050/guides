import { randomUUID } from "node:crypto";
import type {
  BoardItem,
  BoardRole,
  BoardSnapshot,
  BoardSummary,
  LoginRequest,
  PublicUser,
  SessionUser
} from "@board/contracts";

// [Implementation 4]
// AppRepository는 HTTP·WebSocket을 저장 방식에서 분리하는 port입니다.
// MemoryRepository는 같은 권한·version·sequence 계약을 빠르게 관찰하는 adapter이지 별도 업무 정본이 아닙니다.
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
  createItem(boardId: string, actorId: string, input: Pick<BoardItem, "kind" | "content" | "x" | "y">): Promise<{ item: BoardItem; sequence: number; boardVersion: number }>;
  updateItem(boardId: string, actorId: string, itemId: string, content: string, baseVersion: number): Promise<{ item: BoardItem; sequence: number; boardVersion: number } | null>;
  persistItemMove(boardId: string, actorId: string, itemId: string, x: number, y: number, baseVersion: number): Promise<{ item: BoardItem; sequence: number; boardVersion: number } | null>;
  listAdminUsers(): Promise<Array<PublicUser & { status: "active" | "suspended" }>>;
  listAdminActions(): Promise<AdminAction[]>;
  setUserStatus(actorId: string, targetUserId: string, status: "active" | "suspended", reason: string): Promise<void>;
}

type StoredBoard = { id: string; ownerId: string; title: string; version: number; closed: boolean };
type StoredUser = SessionUser;

export class MemoryRepository implements AppRepository {
  private readonly users = new Map<string, StoredUser>();
  private readonly sessions = new Map<string, string>();
  private readonly boards = new Map<string, StoredBoard>();
  private readonly members = new Map<string, Map<string, BoardRole>>();
  private readonly items = new Map<string, Map<string, BoardItem>>();
  private readonly events = new Map<string, BoardEventRecord[]>();
  private readonly actions: AdminAction[] = [];

  async close() {}

  async seed() {
    for (const input of [
      { handle: "owner", displayName: "보드 소유자" },
      { handle: "editor", displayName: "편집자" },
      { handle: "viewer", displayName: "읽기 전용 사용자" },
      { handle: "admin", displayName: "운영자" }
    ]) await this.upsertUser(input);
    const owner = [...this.users.values()].find((user) => user.handle === "owner")!;
    const editor = [...this.users.values()].find((user) => user.handle === "editor")!;
    const viewer = [...this.users.values()].find((user) => user.handle === "viewer")!;
    if (this.boards.size === 0) {
      const board = await this.createBoard(owner.id, "제품 발견 보드");
      this.members.get(board.id)!.set(editor.id, "editor");
      this.members.get(board.id)!.set(viewer.id, "viewer");
      await this.createItem(board.id, owner.id, { kind: "note", content: "첫 번째 가설", x: 120, y: 100 });
    }
  }

  async upsertUser(input: LoginRequest) {
    const existing = [...this.users.values()].find((user) => user.handle === input.handle);
    if (existing) {
      existing.displayName = input.displayName;
      return { ...existing };
    }
    const user: StoredUser = {
      id: randomUUID(),
      ...input,
      role: input.handle === "admin" ? "admin" : "user",
      status: "active"
    };
    this.users.set(user.id, user);
    return { ...user };
  }

  async createSession(userId: string) {
    const token = randomUUID();
    this.sessions.set(token, userId);
    return token;
  }
  async getSessionUser(token: string | undefined) {
    const user = token ? this.users.get(this.sessions.get(token) ?? "") : undefined;
    return user ? { ...user } : null;
  }
  async deleteSession(token: string | undefined) {
    if (token) this.sessions.delete(token);
  }
  async listBoards(userId: string) {
    const result: BoardSummary[] = [];
    for (const board of this.boards.values()) {
      const role = this.members.get(board.id)?.get(userId);
      if (role) result.push({ id: board.id, title: board.title, role, version: board.version, closed: board.closed });
    }
    return result;
  }
  async createBoard(ownerId: string, title: string) {
    const board: StoredBoard = { id: randomUUID(), ownerId, title, version: 0, closed: false };
    this.boards.set(board.id, board);
    this.members.set(board.id, new Map([[ownerId, "owner"]]));
    this.items.set(board.id, new Map());
    this.events.set(board.id, []);
    return { id: board.id, title, role: "owner" as const, version: 0, closed: false };
  }
  async getBoardSnapshot(boardId: string, userId: string) {
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
  async getBoardRole(boardId: string, userId: string) {
    return this.members.get(boardId)?.get(userId) ?? null;
  }
  async inviteMember(boardId: string, actorId: string, handle: string, role: Exclude<BoardRole, "owner">) {
    this.assertOwner(boardId, actorId);
    const user = [...this.users.values()].find((candidate) => candidate.handle === handle);
    if (!user) throw new Error("user_not_found");
    this.members.get(boardId)!.set(user.id, role);
  }
  async changeMemberRole(boardId: string, actorId: string, userId: string, role: Exclude<BoardRole, "owner">) {
    this.assertOwner(boardId, actorId);
    if (!this.members.get(boardId)?.has(userId)) throw new Error("member_not_found");
    this.members.get(boardId)!.set(userId, role);
  }
  async listBoardEvents(boardId: string, userId: string) {
    if (!this.members.get(boardId)?.has(userId)) throw new Error("forbidden");
    return [...(this.events.get(boardId) ?? [])].reverse();
  }
  async createItem(boardId: string, actorId: string, input: Pick<BoardItem, "kind" | "content" | "x" | "y">) {
    this.assertWritable(boardId, actorId);
    const item: BoardItem = { id: randomUUID(), boardId, ...input, width: 240, height: 140, version: 1 };
    this.items.get(boardId)!.set(item.id, item);
    return this.record(boardId, actorId, "item.create", item, item);
  }
  async updateItem(boardId: string, actorId: string, itemId: string, content: string, baseVersion: number) {
    this.assertWritable(boardId, actorId);
    const item = this.items.get(boardId)?.get(itemId);
    if (!item || item.version !== baseVersion) return null;
    item.content = content;
    item.version += 1;
    return this.record(boardId, actorId, "item.update", { itemId, content }, item);
  }
  async persistItemMove(boardId: string, actorId: string, itemId: string, x: number, y: number, baseVersion: number) {
    this.assertWritable(boardId, actorId);
    const item = this.items.get(boardId)?.get(itemId);
    if (!item || item.version !== baseVersion) return null;
    item.x = x;
    item.y = y;
    item.version += 1;
    return this.record(boardId, actorId, "item.move", { itemId, x, y }, item);
  }
  async listAdminUsers() {
    return [...this.users.values()].map(({ role: _role, ...user }) => user);
  }
  async listAdminActions() {
    return [...this.actions].reverse();
  }
  async setUserStatus(actorId: string, targetUserId: string, status: "active" | "suspended", reason: string) {
    const target = this.users.get(targetUserId);
    if (!target) throw new Error("user_not_found");
    target.status = status;
    this.actions.push({
      id: randomUUID(),
      actorId,
      targetUserId,
      action: status === "suspended" ? "suspend" : "restore",
      reason,
      createdAt: new Date().toISOString()
    });
    if (status === "suspended") {
      for (const [token, userId] of this.sessions) if (userId === targetUserId) this.sessions.delete(token);
    }
  }

  private record(boardId: string, actorId: string, eventType: string, payload: unknown, item: BoardItem) {
    const board = this.boards.get(boardId)!;
    const events = this.events.get(boardId)!;
    board.version += 1;
    const event: BoardEventRecord = {
      id: randomUUID(),
      boardId,
      sequence: (events.at(-1)?.sequence ?? 0) + 1,
      actorId,
      eventType,
      payload,
      createdAt: new Date().toISOString()
    };
    events.push(event);
    return { item: { ...item }, sequence: event.sequence, boardVersion: board.version };
  }
  private assertOwner(boardId: string, actorId: string) {
    if (this.members.get(boardId)?.get(actorId) !== "owner") throw new Error("forbidden");
  }
  private assertWritable(boardId: string, actorId: string) {
    const role = this.members.get(boardId)?.get(actorId);
    if (role !== "owner" && role !== "editor") throw new Error("read_only");
  }
}

export function createMemoryRepository(): AppRepository {
  return new MemoryRepository();
}
export { createPostgresRepository } from "./postgres";
export type { Database } from "./db-types";
