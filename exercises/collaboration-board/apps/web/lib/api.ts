import {
  BoardSnapshotSchema,
  BoardSummarySchema,
  SessionUserSchema,
  type BoardSnapshot,
  type BoardSummary,
  type SessionUser
} from "@board/contracts";
import { z } from "zod";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:4000";
export const websocketUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:4000/ws";

const ApiErrorSchema = z.object({
  code: z.string(),
  message: z.string().optional()
});

export class ApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string) {
    super(message);
  }
}

// [Implementation 9-1] Centralize credentialed HTTP transport, status handling, and runtime response parsing so components never trust arbitrary JSON directly.
async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  init: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body ? { "content-type": "application/json" } : {}),
      ...init.headers
    }
  });
  if (!response.ok) {
    const parsed = ApiErrorSchema.safeParse(await response.json().catch(() => null));
    throw new ApiError(
      response.status,
      parsed.success ? parsed.data.code : "request_failed",
      parsed.success ? parsed.data.message ?? "Request failed." : "Request failed."
    );
  }
  if (response.status === 204) return undefined as T;
  return schema.parse(await response.json());
}

export async function login(input: { handle: string; displayName: string }): Promise<SessionUser> {
  return (await request("/auth/login", z.object({ user: SessionUserSchema }), {
    method: "POST",
    body: JSON.stringify(input)
  })).user;
}

export async function logout(): Promise<void> {
  await request("/auth/logout", z.object({ ok: z.literal(true) }), { method: "POST" });
}

export async function getMe(): Promise<SessionUser> {
  return (await request("/me", z.object({ user: SessionUserSchema }))).user;
}

export async function listBoards(): Promise<BoardSummary[]> {
  return (await request("/boards", z.object({ boards: z.array(BoardSummarySchema) }))).boards;
}

export async function createBoard(title: string): Promise<BoardSummary> {
  return (await request("/boards", z.object({ board: BoardSummarySchema }), {
    method: "POST",
    body: JSON.stringify({ title })
  })).board;
}

export async function getBoard(boardId: string): Promise<BoardSnapshot> {
  return (await request(`/boards/${boardId}`, z.object({ board: BoardSnapshotSchema }))).board;
}

export const BoardEventSchema = z.object({
  id: z.string().uuid(),
  boardId: z.string().uuid(),
  sequence: z.number().int(),
  actorId: z.string().uuid(),
  eventType: z.string(),
  payload: z.unknown(),
  createdAt: z.string().datetime()
});
export type BoardEvent = z.infer<typeof BoardEventSchema>;

export async function listActivity(boardId: string): Promise<BoardEvent[]> {
  return (await request(`/boards/${boardId}/activity`, z.object({ events: z.array(BoardEventSchema) }))).events;
}

export const AdminUserSchema = z.object({
  id: z.string().uuid(),
  handle: z.string(),
  displayName: z.string(),
  status: z.enum(["active", "suspended"])
});
export type AdminUser = z.infer<typeof AdminUserSchema>;

export const AdminActionSchema = z.object({
  id: z.string().uuid(),
  actorId: z.string().uuid(),
  targetUserId: z.string().uuid(),
  action: z.enum(["suspend", "restore"]),
  reason: z.string(),
  createdAt: z.string().datetime()
});
export type AdminAction = z.infer<typeof AdminActionSchema>;

export async function listAdminUsers(): Promise<AdminUser[]> {
  return (await request("/admin/users", z.object({ users: z.array(AdminUserSchema) }))).users;
}

export async function listAdminActions(): Promise<AdminAction[]> {
  return (await request("/admin/actions", z.object({ actions: z.array(AdminActionSchema) }))).actions;
}

export async function setUserStatus(
  userId: string,
  status: "active" | "suspended",
  reason: string
): Promise<void> {
  await request(`/admin/users/${userId}/status`, z.void(), {
    method: "PATCH",
    body: JSON.stringify({ status, reason })
  });
}
