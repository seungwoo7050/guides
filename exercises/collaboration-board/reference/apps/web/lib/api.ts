import {
  BoardSnapshotSchema,
  BoardSummarySchema,
  SessionUserSchema,
  type LoginRequest,
  type SessionUser
} from "@board/contracts";

// [Implementation 6-3]
// HTTP 세부 사항과 response runtime parsing을 adapter에 모아 component가 URL·cookie·wire shape를 직접 소유하지 않게 합니다.
// non-2xx는 성공 DTO로 흘려보내지 않고 호출한 UI state가 복구 경로를 선택하게 합니다.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:4000";

async function request(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("content-type")) headers.set("content-type", "application/json");
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) throw new Error(await response.text());
  if (response.status === 204) return null;
  return response.json() as Promise<unknown>;
}

export async function login(input: LoginRequest): Promise<SessionUser> {
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify(input)
  }) as { user: unknown };
  return SessionUserSchema.parse(data.user);
}
export async function logout() {
  await request("/auth/logout", { method: "POST" });
}
export async function getMe() {
  try {
    const data = await request("/me") as { user: unknown };
    return SessionUserSchema.parse(data.user);
  } catch {
    return null;
  }
}
export async function listBoards(signal?: AbortSignal) {
  const data = await request("/boards", { signal }) as { boards: unknown[] };
  return data.boards.map((board) => BoardSummarySchema.parse(board));
}
export async function createBoard(title: string) {
  const data = await request("/boards", {
    method: "POST",
    body: JSON.stringify({ title })
  }) as { board: unknown };
  return BoardSummarySchema.parse(data.board);
}
export async function getBoard(boardId: string) {
  const data = await request(`/boards/${encodeURIComponent(boardId)}`) as { board: unknown };
  return BoardSnapshotSchema.parse(data.board);
}
export async function getActivity(boardId: string) {
  const data = await request(`/boards/${encodeURIComponent(boardId)}/activity`) as { events: unknown[] };
  return data.events;
}
export async function inviteMember(boardId: string, handle: string, role: "editor" | "viewer") {
  await request(`/boards/${encodeURIComponent(boardId)}/invitations`, {
    method: "POST",
    body: JSON.stringify({ handle, role })
  });
}
export async function getAdminUsers() {
  return (await request("/admin/users") as {
    users: Array<{ id: string; displayName: string; handle: string; status: "active" | "suspended" }>
  }).users;
}
export async function setUserStatus(
  id: string,
  status: "active" | "suspended",
  reason: string
) {
  await request(`/admin/users/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, reason })
  });
}
