import { describe, expect, it } from "vitest";
import { buildApp } from "./app";

function cookieOf(response: { headers: Record<string, string | string[] | number | undefined> }) {
  const value = response.headers["set-cookie"];
  return String(Array.isArray(value) ? value[0] : value).split(";")[0];
}

describe("security boundaries", () => {
  const trustedOrigin = "http://localhost:3000";

  it("distinguishes authentication, role and ownership failures", async () => {
    const app = buildApp();
    await app.ready();
    expect((await app.inject({ method: "GET", url: "/me" })).statusCode).toBe(401);
    const login = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
    const cookie = cookieOf(login);
    expect(String(login.headers["set-cookie"])).toContain("HttpOnly");
    expect(String(login.headers["set-cookie"])).toContain("SameSite=Lax");
    expect(String(login.headers["set-cookie"])).toContain("Path=/");
    expect((await app.inject({ method: "GET", url: "/admin/users", headers: { cookie } })).statusCode).toBe(403);
    expect((await app.inject({
      method: "PATCH",
      url: "/profiles/u-admin",
      headers: { cookie, origin: trustedOrigin },
      payload: { displayName: "x" }
    })).statusCode).toBe(403);
    await app.close();
  });

  it("rejects an untrusted Origin before mutating authenticated state", async () => {
    const app = buildApp();
    await app.ready();
    const login = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
    const response = await app.inject({
      method: "PATCH",
      url: "/profiles/u-alpha",
      headers: { cookie: cookieOf(login), origin: "https://attacker.invalid" },
      payload: { displayName: "attacker changed this" }
    });
    expect(response.statusCode).toBe(403);
    expect(response.json()).toEqual({ code: "origin_forbidden" });
    const deceptiveSuffix = await app.inject({
      method: "PATCH",
      url: "/profiles/u-alpha",
      headers: { cookie: cookieOf(login), origin: "https://evil-localhost:3000" },
      payload: { displayName: "deceptive suffix" }
    });
    expect(deceptiveSuffix.statusCode).toBe(403);
    expect(deceptiveSuffix.json()).toEqual({ code: "origin_forbidden" });
    const missingOrigin = await app.inject({
      method: "PATCH",
      url: "/profiles/u-alpha",
      headers: { cookie: cookieOf(login) },
      payload: { displayName: "missing Origin" }
    });
    expect(missingOrigin.statusCode).toBe(403);
    expect(missingOrigin.json()).toEqual({ code: "origin_forbidden" });
    await app.close();
  });

  it("revokes the server session on logout", async () => {
    const app = buildApp();
    await app.ready();
    const login = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
    const cookie = cookieOf(login);
    expect((await app.inject({
      method: "POST",
      url: "/auth/logout",
      headers: { cookie, origin: trustedOrigin }
    })).statusCode).toBe(200);
    expect((await app.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(401);
    await app.close();
  });
});
