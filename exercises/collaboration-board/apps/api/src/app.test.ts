import { describe, expect, it } from "vitest";
import type { WebSocket } from "ws";

import { createMemoryRepository } from "@board/db";
import { buildApp } from "./app";

const origin = "http://localhost:3000";

function cookieOf(response: { headers: Record<string, string | string[] | number | undefined> }): string {
  const value = response.headers["set-cookie"];
  return String(Array.isArray(value) ? value[0] : value).split(";")[0] ?? "";
}

function closed(socket: WebSocket): Promise<number> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("close timeout")), 1_000);
    socket.once("close", (code) => {
      clearTimeout(timer);
      resolve(code);
    });
  });
}

function nextMessage(socket: WebSocket, type: string): Promise<Record<string, unknown>> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`message timeout: ${type}`)), 1_000);
    const handler = (raw: unknown) => {
      const message = JSON.parse(String(raw)) as Record<string, unknown>;
      if (message.type !== type) return;
      clearTimeout(timer);
      socket.off("message", handler);
      resolve(message);
    };
    socket.on("message", handler);
  });
}

describe("board HTTP API", () => {
  it("separates authentication, owner membership, and exact Origin policy", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const app = buildApp(repo, { allowedOrigins: [origin], logger: false, heartbeatIntervalMs: 100_000 });
    await app.ready();
    try {
      expect((await app.inject({ method: "GET", url: "/boards" })).statusCode).toBe(401);
      const login = await app.inject({
        method: "POST",
        url: "/auth/login",
        payload: { handle: "owner", displayName: "Owner" }
      });
      const cookie = cookieOf(login);
      expect(String(login.headers["set-cookie"])).toContain("HttpOnly");

      const rejected = await app.inject({
        method: "POST",
        url: "/boards",
        headers: { cookie, origin: "https://attacker.invalid" },
        payload: { title: "Rejected" }
      });
      expect(rejected.statusCode).toBe(403);

      const created = await app.inject({
        method: "POST",
        url: "/boards",
        headers: { cookie, origin },
        payload: { title: "Roadmap" }
      });
      expect(created.statusCode).toBe(201);
      expect(created.json().board).toMatchObject({ title: "Roadmap", role: "owner" });
    } finally {
      await app.close();
    }
  });

  it("disconnects an active board socket when its membership role changes", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const app = buildApp(repo, { allowedOrigins: [origin], logger: false, heartbeatIntervalMs: 100_000 });
    await app.ready();
    try {
      const ownerLogin = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "owner", displayName: "Owner" } });
      const editorLogin = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "editor", displayName: "Editor" } });
      const ownerCookie = cookieOf(ownerLogin);
      const editorCookie = cookieOf(editorLogin);
      const owner = ownerLogin.json().user as { id: string };
      const editor = editorLogin.json().user as { id: string };
      expect(owner.id).not.toBe(editor.id);

      const boards = (await app.inject({ method: "GET", url: "/boards", headers: { cookie: ownerCookie } })).json().boards as Array<{ id: string }>;
      const boardId = boards[0]?.id;
      expect(boardId).toBeTruthy();

      const editorSocket = await app.injectWS("/ws", { headers: { cookie: editorCookie, origin } }) as WebSocket;
      const snapshot = nextMessage(editorSocket, "board.snapshot");
      editorSocket.send(JSON.stringify({ type: "board.join", boardId }));
      await snapshot;
      const closeCode = closed(editorSocket);

      const changed = await app.inject({
        method: "PATCH",
        url: `/boards/${boardId}/members/${editor.id}/role`,
        headers: { cookie: ownerCookie, origin },
        payload: { role: "viewer" }
      });
      expect(changed.statusCode).toBe(204);
      expect(await closeCode).toBe(1008);
    } finally {
      await app.close();
    }
  });

  it("revokes a suspended user's existing session", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const app = buildApp(repo, { allowedOrigins: [origin], logger: false, heartbeatIntervalMs: 100_000 });
    await app.ready();
    try {
      const editorLogin = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "editor", displayName: "Editor" } });
      const adminLogin = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "admin", displayName: "Admin" } });
      const editorCookie = cookieOf(editorLogin);
      const adminCookie = cookieOf(adminLogin);
      const editorSocket = await app.injectWS("/ws", { headers: { cookie: editorCookie, origin } }) as WebSocket;
      const closeCode = closed(editorSocket);

      const users = (await app.inject({ method: "GET", url: "/admin/users", headers: { cookie: adminCookie } })).json().users;
      const editor = users.find((user: { handle: string }) => user.handle === "editor");
      const suspended = await app.inject({
        method: "PATCH",
        url: `/admin/users/${editor.id}/status`,
        headers: { cookie: adminCookie, origin },
        payload: { status: "suspended", reason: "test" }
      });
      expect(suspended.statusCode).toBe(204);
      expect(await closeCode).toBe(1008);
      expect((await app.inject({ method: "GET", url: "/me", headers: { cookie: editorCookie } })).statusCode).toBe(401);
    } finally {
      await app.close();
    }
  });
});
