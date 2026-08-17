import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import websocket from "@fastify/websocket";
import Fastify, { type FastifyReply, type FastifyRequest } from "fastify";
import type { WebSocket } from "ws";

import {
  ChangeMemberRoleSchema,
  ChangeUserStatusSchema,
  CreateBoardSchema,
  InviteMemberSchema,
  LoginRequestSchema
} from "@board/contracts";
import { RepositoryError, type AppRepository } from "@board/db";
import { BoardHub } from "./boardHub";

const SESSION_COOKIE = "board_session";
const MUTATION_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

export interface AppOptions {
  allowedOrigins?: readonly string[];
  logger?: boolean;
  heartbeatIntervalMs?: number;
}

// [Implementation 6] Compose repository injection, credentialed CORS, cookie parsing, HTTP routes, and authenticated WebSocket admission without opening a network listener on import.
export function buildApp(repo: AppRepository, options: AppOptions = {}) {
  const allowedOrigins = new Set(options.allowedOrigins ?? ["http://localhost:3000"]);
  const app = Fastify({
    logger: options.logger === false ? false : {
      level: process.env.LOG_LEVEL ?? "info",
      redact: ["req.headers.authorization", "req.headers.cookie"]
    }
  });
  const hub = new BoardHub(repo, options.heartbeatIntervalMs);

  app.register(cors, {
    origin: [...allowedOrigins],
    credentials: true,
    methods: ["GET", "POST", "PATCH", "OPTIONS"],
    allowedHeaders: ["content-type"]
  });
  app.register(cookie);
  app.register(websocket);

  app.addHook("preHandler", async (request, reply) => {
    if (!MUTATION_METHODS.has(request.method)) return;
    if (!request.cookies[SESSION_COOKIE]) return;
    const origin = request.headers.origin;
    if (!origin || !allowedOrigins.has(origin)) {
      return reply.code(403).send({ code: "origin_forbidden", message: "Origin is not allowed." });
    }
  });

  app.after(() => {
    app.get("/ws", { websocket: true }, (socket, request) => {
      const origin = request.headers.origin;
      if (!origin || !allowedOrigins.has(origin)) {
        socket.close(1008, "origin forbidden");
        return;
      }
      currentUser(repo, request)
        .then((user) => {
          if (!user) return socket.close(1008, "unauthorized");
          if (user.status !== "active") return socket.close(1008, "account suspended");
          hub.connect(socket as WebSocket, user);
        })
        .catch(() => socket.close(1011, "authentication failed"));
    });
  });

  app.get("/health", async () => ({ ok: true, service: "board-api" }));

  // [Implementation 6-1] Issue and revoke opaque server sessions with one constrained cookie while distinguishing inactive, unauthenticated, and unauthorized identities.
  app.post("/auth/login", async (request, reply) => {
    const parsed = LoginRequestSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply);
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

  // [Implementation 6-2] Keep HTTP routes responsible for validation and status translation while membership, optimistic mutation, and transaction rules remain behind the repository port.
  app.get("/boards", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    return user ? { boards: await repo.listBoards(user.id) } : undefined;
  });

  app.post("/boards", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const parsed = CreateBoardSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply);
    return reply.code(201).send({ board: await repo.createBoard(user.id, parsed.data.title) });
  });

  app.get("/boards/:id", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const { id } = request.params as { id: string };
    const board = await repo.getBoardSnapshot(id, user.id);
    return board ? { board } : reply.code(404).send({ code: "not_found", message: "Board was not found." });
  });

  app.get("/boards/:id/activity", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const { id } = request.params as { id: string };
    try {
      return { events: await repo.listBoardEvents(id, user.id) };
    } catch (error) {
      return repositoryFailure(reply, error);
    }
  });

  app.post("/boards/:id/invitations", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const parsed = InviteMemberSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply);
    const { id } = request.params as { id: string };
    try {
      await repo.inviteMember(id, user.id, parsed.data.handle, parsed.data.role);
      return reply.code(204).send();
    } catch (error) {
      return repositoryFailure(reply, error);
    }
  });

  app.patch("/boards/:id/members/:userId/role", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const parsed = ChangeMemberRoleSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply);
    const { id, userId } = request.params as { id: string; userId: string };
    try {
      await repo.changeMemberRole(id, user.id, userId, parsed.data.role);
      hub.disconnectBoardMember(id, userId, "membership role changed");
      return reply.code(204).send();
    } catch (error) {
      return repositoryFailure(reply, error);
    }
  });

  app.post("/boards/:id/close", async (request, reply) => {
    const user = await requireUser(repo, request, reply);
    if (!user) return;
    const { id } = request.params as { id: string };
    try {
      await repo.closeBoard(id, user.id);
      hub.broadcastBoardClosed(id, "board closed by owner");
      return reply.code(204).send();
    } catch (error) {
      return repositoryFailure(reply, error);
    }
  });

  // [Implementation 6-3] Recheck active admin role on every privileged request and make suspension atomically invalidate the target user's existing sessions.
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
    const parsed = ChangeUserStatusSchema.safeParse(request.body);
    if (!parsed.success) return invalid(reply);
    const { id } = request.params as { id: string };
    try {
      await repo.setUserStatus(actor.id, id, parsed.data.status, parsed.data.reason);
      if (parsed.data.status === "suspended") hub.disconnectUser(id, "account suspended");
      return reply.code(204).send();
    } catch (error) {
      return repositoryFailure(reply, error);
    }
  });

  // [Implementation 6-4] Use Fastify close as the single owner of heartbeat, socket, room, and repository resource teardown.
  app.addHook("onClose", async () => {
    hub.close();
    await repo.close();
  });

  return app;
}

export function readSessionToken(request: FastifyRequest): string | undefined {
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

function invalid(reply: FastifyReply) {
  return reply.code(400).send({ code: "invalid_request", message: "Request body is invalid." });
}

function unauthorized(reply: FastifyReply) {
  return reply.code(401).send({ code: "unauthorized", message: "Authentication is required." });
}

function forbidden(reply: FastifyReply) {
  return reply.code(403).send({ code: "forbidden", message: "Permission is required." });
}

function repositoryFailure(reply: FastifyReply, error: unknown) {
  if (!(error instanceof RepositoryError)) throw error;
  if (error.code === "user_not_found" || error.code === "member_not_found") {
    return reply.code(404).send({ code: error.code, message: "Resource was not found." });
  }
  if (error.code === "board_closed") {
    return reply.code(409).send({ code: error.code, message: "Board is closed." });
  }
  return forbidden(reply);
}
