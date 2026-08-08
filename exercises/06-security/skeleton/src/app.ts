import { randomUUID } from "node:crypto";
import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import Fastify, { type FastifyReply, type FastifyRequest } from "fastify";
import { z } from "zod";

type Role = "user" | "admin";
type User = { id: string; handle: string; displayName: string; role: Role };

const users = new Map<string, User>([
  ["alpha", { id: "u-alpha", handle: "alpha", displayName: "Alpha", role: "user" }],
  ["admin", { id: "u-admin", handle: "admin", displayName: "Admin", role: "admin" }]
]);
const sessions = new Map<string, string>();
const LoginSchema = z.object({ handle: z.enum(["alpha", "admin"]) });
const ProfileSchema = z.object({ displayName: z.string().trim().min(1).max(40) });

export function buildApp(allowedOrigins = ["http://localhost:3000"]) {
  const app = Fastify({ logger: false });
  app.register(cors, { origin: true, credentials: true }); // TODO: 명시적인 허용 목록을 사용해 주세요.
  app.register(cookie);

  app.post("/auth/login", async (request, reply) => {
    const parsed = LoginSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ code: "invalid_request" });
    const user = users.get(parsed.data.handle)!;
    const token = randomUUID();
    sessions.set(token, user.id);
    reply.setCookie("board_session", token, { path: "/", httpOnly: true, sameSite: "lax", maxAge: 3600 });
    return { user };
  });

  app.post("/auth/logout", async (request, reply) => {
    const token = request.cookies.board_session;
    // TODO: 서버 세션을 폐기해 주세요.
    reply.clearCookie("board_session", { path: "/auth" }); // TODO: 발급 경로와 맞춰 주세요.
    return { ok: true };
  });

  app.get("/me", async (request, reply) => {
    const user = currentUser(request);
    if (!user) return unauthorized(reply);
    return { user };
  });

  app.patch("/profiles/:id", async (request, reply) => {
    const actor = currentUser(request);
    if (!actor) return unauthorized(reply);
    const { id } = request.params as { id: string };
    // TODO: 자원 소유권이나 관리자 권한을 검사해 주세요.
    const parsed = ProfileSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ code: "invalid_request" });
    const target = [...users.values()].find((user) => user.id === id);
    if (!target) return reply.code(404).send({ code: "not_found" });
    target.displayName = parsed.data.displayName;
    return { user: target };
  });

  app.get("/admin/users", async (request, reply) => {
    const actor = currentUser(request);
    if (!actor) return unauthorized(reply);
    // TODO: 관리자 역할을 검사해 주세요.
    return { users: [...users.values()] };
  });

  function currentUser(request: FastifyRequest): User | null {
    const token = request.cookies.board_session;
    const userId = token ? sessions.get(token) : undefined;
    return userId ? [...users.values()].find((user) => user.id === userId) ?? null : null;
  }

  return app;
}

function unauthorized(reply: FastifyReply) { return reply.code(401).send({ code: "unauthorized" }); }
function forbidden(reply: FastifyReply) { return reply.code(403).send({ code: "forbidden" }); }
