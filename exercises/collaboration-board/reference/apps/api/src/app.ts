import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import websocket from "@fastify/websocket";
import Fastify, { type FastifyReply, type FastifyRequest } from "fastify";
import type { WebSocket } from "ws";
import { z } from "zod";
import {
  ChangeMemberRoleSchema,
  CreateBoardSchema,
  InviteMemberSchema,
  LoginRequestSchema
} from "@board/contracts";
import type { AppRepository } from "@board/db";
import { BoardHub } from "./boardHub";

const SESSION_COOKIE = "board_session";

// [Implementation 5]
// app factory가 Fastify plugin, HTTP·WebSocket 정책과 repository 수명을 소유하면 test는 port 없이 같은 app을 주입할 수 있습니다.
// module import만으로 listen하거나 resource를 만들지 않고 composition root가 adapter와 origin을 전달합니다.
export function buildApp(
  repo: AppRepository,
  options: { allowedOrigins: string[] } = { allowedOrigins: ["http://localhost:3000"] }
) {
  const app = Fastify({
    logger: {
      level: process.env.LOG_LEVEL ?? "info",
      redact: ["req.headers.authorization", "req.headers.cookie"]
    }
  });
  app.register(cors, {
    origin: options.allowedOrigins,
    credentials: true,
    methods: ["GET", "POST", "PATCH", "OPTIONS"],
    allowedHeaders: ["content-type"]
  });
  app.register(cookie);
  const hub = new BoardHub(repo);

  app.register(websocket);
  app.after(() => {
    app.get("/ws", { websocket: true }, (socket, request) => {
      const origin = request.headers.origin;
      if (origin && !options.allowedOrigins.includes(origin)) return socket.close(1008, "origin forbidden");
      currentUser(repo, request).then((user) => {
        if (!user) return socket.close(1008, "unauthorized");
        if (user.status !== "active") return socket.close(1008, "account suspended");
        hub.connect(socket as WebSocket, user);
      }).catch(() => socket.close(1011, "authentication failed"));
    });
  });

  app.addHook("preHandler", async (request, reply) => {
    if (["POST", "PATCH", "PUT", "DELETE"].includes(request.method)) {
      const origin = request.headers.origin;
      if (origin && !options.allowedOrigins.includes(origin)) {
        return reply.code(403).send({ code: "origin_forbidden", message: "허용되지 않은 출처입니다." });
      }
    }
  });

  app.get("/health", async () => ({ ok: true, service: "board-api" }));

  // [Implementation 5-1]
  // 인증 성공은 browser cookie와 server session을 함께 만들고, logout은 같은 path의 cookie와 server state를 함께 폐기합니다.
  app.post("/auth/login", async (request, reply) => {
    const parsed = LoginRequestSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply, parsed.error.issues);
    const user = await repo.upsertUser(parsed.data);
    if (user.status !== "active") return forbidden(reply);
    const token = await repo.createSession(user.id);
    reply.setCookie(SESSION_COOKIE, token, {
      path: "/",
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      maxAge: 14 * 24 * 60 * 60
    });
    return { user };
  });
  app.post("/auth/logout", async (request, reply) => {
    await repo.deleteSession(readSessionToken(request));
    reply.clearCookie(SESSION_COOKIE, { path: "/" });
    return { ok: true };
  });
  app.get("/me", async (request, reply) => {
    const user = await currentUser(repo, request);
    return user ? { user } : unauthorized(reply);
  });
  // [Implementation 5-2]
  // board route는 transport validation과 HTTP status만 소유하고 membership·transaction은 repository 계약에 위임합니다.
  app.get("/boards", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    return user ? { boards: await repo.listBoards(user.id) } : undefined;
  });
  app.post("/boards", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const parsed = CreateBoardSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply, parsed.error.issues);
    return reply.code(201).send({ board: await repo.createBoard(user.id, parsed.data.title) });
  });
  app.get("/boards/:id", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const { id } = request.params as { id: string };
    const board = await repo.getBoardSnapshot(id, user.id);
    return board ? { board } : reply.code(404).send({ code: "not_found", message: "보드를 찾을 수 없습니다." });
  });
  app.get("/boards/:id/activity", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const { id } = request.params as { id: string };
    try {
      return { events: await repo.listBoardEvents(id, user.id) };
    } catch {
      return forbidden(reply);
    }
  });
  app.post("/boards/:id/invitations", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const parsed = InviteMemberSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply, parsed.error.issues);
    const { id } = request.params as { id: string };
    try {
      await repo.inviteMember(id, user.id, parsed.data.handle, parsed.data.role);
      return reply.code(204).send();
    } catch {
      return forbidden(reply);
    }
  });
  app.patch("/boards/:id/members/:userId/role", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const parsed = ChangeMemberRoleSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply, parsed.error.issues);
    const { id, userId } = request.params as { id: string; userId: string };
    try {
      await repo.changeMemberRole(id, user.id, userId, parsed.data.role);
      return reply.code(204).send();
    } catch {
      return forbidden(reply);
    }
  });
  // [Implementation 5-3]
  // 관리 화면을 숨기는 것과 별개로 server가 매 요청에서 active admin role을 다시 확인합니다.
  app.get("/admin/users", async (request, reply) => {
    const actor = await requireAdmin(repo, request, reply);
    return actor ? { users: await repo.listAdminUsers() } : undefined;
  });
  app.get("/admin/actions", async (request, reply) => {
    const actor = await requireAdmin(repo, request, reply);
    return actor ? { actions: await repo.listAdminActions() } : undefined;
  });
  app.patch("/admin/users/:id/status", async (request, reply) => {
    const actor = await requireAdmin(repo, request, reply);
    if (!actor) return;
    const parsed = z.object({
      status: z.enum(["active", "suspended"]),
      reason: z.string().trim().min(1).max(200)
    }).safeParse(request.body);
    if (!parsed.success) return invalid(reply, parsed.error.issues);
    const { id } = request.params as { id: string };
    await repo.setUserStatus(actor.id, id, parsed.data.status, parsed.data.reason);
    return reply.code(204).send();
  });

  // [Implementation 5-4]
  // Fastify 종료를 hub heartbeat/socket과 repository pool의 단일 lifecycle owner로 사용합니다.
  app.addHook("onClose", async () => {
    hub.close();
    await repo.close();
  });
  return app;
}

export function readSessionToken(request: FastifyRequest) {
  return request.cookies?.[SESSION_COOKIE];
}
export async function currentUser(repo: AppRepository, request: FastifyRequest) {
  return repo.getSessionUser(readSessionToken(request));
}
async function requireUser(repo: AppRepository, request: FastifyRequest, reply: FastifyReply) {
  const user = await currentUser(repo, request);
  if (!user) {
    unauthorized(reply);
    return null;
  }
  if (user.status !== "active") {
    forbidden(reply);
    return null;
  }
  return user;
}
async function requireAdmin(repo: AppRepository, request: FastifyRequest, reply: FastifyReply) {
  const user = await requireUser(repo, request, reply);
  if (!user || user.role !== "admin") {
    if (user) forbidden(reply);
    return null;
  }
  return user;
}
function invalid(reply: FastifyReply, issues: unknown) {
  return reply.code(400).send({ code: "invalid_request", message: "요청 형식이 올바르지 않습니다.", issues });
}
function unauthorized(reply: FastifyReply) {
  return reply.code(401).send({ code: "unauthorized", message: "로그인이 필요합니다." });
}
function forbidden(reply: FastifyReply) {
  return reply.code(403).send({ code: "forbidden", message: "권한이 없습니다." });
}
