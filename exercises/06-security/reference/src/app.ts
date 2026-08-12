import { randomUUID } from "node:crypto";
import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import Fastify, { type FastifyReply, type FastifyRequest } from "fastify";
import { z } from "zod";

// [Implementation 1] 사용자, role과 server session을 module state의 명시적 owner로 두고 외부 body schema를 함께 정의합니다.
type Role = "user" | "admin";
type User = { id: string; handle: string; displayName: string; role: Role };

const users = new Map<string, User>([
  ["alpha", { id: "u-alpha", handle: "alpha", displayName: "Alpha", role: "user" }],
  ["admin", { id: "u-admin", handle: "admin", displayName: "Admin", role: "admin" }]
]);
const sessions = new Map<string, string>();
const LoginSchema = z.object({ handle: z.enum(["alpha", "admin"]) });
const ProfileSchema = z.object({ displayName: z.string().trim().min(1).max(40) });

// [Implementation 2] app factory가 credential cookie와 정확한 Origin allowlist를 같은 browser security boundary로 구성합니다.
export function buildApp(allowedOrigins = ["http://localhost:3000"]) {
  const app = Fastify({ logger: false });
  app.register(cors, { origin: allowedOrigins, credentials: true });
  app.register(cookie);

  // [Implementation 3] session cookie가 있는 상태 변경은 허용된 Origin에서만 진행된다는 invariant를 route 전에 강제합니다.
  app.addHook("preHandler", async (request, reply) => {
    const changesState = ["POST", "PUT", "PATCH", "DELETE"].includes(request.method);
    const hasSessionCookie = Boolean(request.cookies.board_session);
    if (!changesState || !hasSessionCookie) return;
    const origin = request.headers.origin;
    if (!origin || !allowedOrigins.includes(origin)) {
      return reply.code(403).send({ code: "origin_forbidden" });
    }
  });

  // [Implementation 4] login은 server-side token state와 제한된 browser cookie를 한 응답에서 발급합니다.
  app.post("/auth/login", async (request, reply) => {
    const parsed = LoginSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ code: "invalid_request" });
    const user = users.get(parsed.data.handle)!;
    const token = randomUUID();
    sessions.set(token, user.id);
    reply.setCookie("board_session", token, {
      path: "/",
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      maxAge: 3600
    });
    return { user };
  });

  // [Implementation 5] logout은 server token과 같은 path의 cookie를 모두 폐기해 한쪽 credential이 남지 않게 합니다.
  app.post("/auth/logout", async (request, reply) => {
    const token = request.cookies.board_session;
    if (token) sessions.delete(token);
    reply.clearCookie("board_session", { path: "/" });
    return { ok: true };
  });

  app.get("/me", async (request, reply) => {
    const user = currentUser(request);
    if (!user) return unauthorized(reply);
    return { user };
  });

  // [Implementation 7] profile 변경은 URL의 id를 신뢰하지 않고 현재 사용자 ownership 또는 admin role을 검사합니다.
  app.patch("/profiles/:id", async (request, reply) => {
    const actor = currentUser(request);
    if (!actor) return unauthorized(reply);
    const { id } = request.params as { id: string };
    if (actor.id !== id && actor.role !== "admin") return forbidden(reply);
    const parsed = ProfileSchema.safeParse(request.body);
    if (!parsed.success) return reply.code(400).send({ code: "invalid_request" });
    const target = [...users.values()].find((user) => user.id === id);
    if (!target) return reply.code(404).send({ code: "not_found" });
    target.displayName = parsed.data.displayName;
    return { user: target };
  });

  // [Implementation 8] admin endpoint는 authentication 뒤 role authorization을 별도 server guard로 적용합니다.
  app.get("/admin/users", async (request, reply) => {
    const actor = currentUser(request);
    if (!actor) return unauthorized(reply);
    if (actor.role !== "admin") return forbidden(reply);
    return { users: [...users.values()] };
  });

  // [Implementation 6] cookie token에서 현재 identity를 복원하고 401과 403 helper가 failure 의미를 분리합니다.
  function currentUser(request: FastifyRequest): User | null {
    const token = request.cookies.board_session;
    const userId = token ? sessions.get(token) : undefined;
    return userId ? [...users.values()].find((user) => user.id === userId) ?? null : null;
  }

  return app;
}

function unauthorized(reply: FastifyReply) { return reply.code(401).send({ code: "unauthorized" }); }
function forbidden(reply: FastifyReply) { return reply.code(403).send({ code: "forbidden" }); }
