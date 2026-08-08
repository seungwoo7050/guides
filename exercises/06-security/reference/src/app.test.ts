import { describe, expect, it } from "vitest";
import { buildApp } from "./app";

function cookieOf(response: { headers: Record<string, string | string[] | number | undefined> }) {
  const value = response.headers["set-cookie"];
  return String(Array.isArray(value) ? value[0] : value).split(";")[0];
}

describe("security boundaries", () => {
  it("revokes logout session and enforces role/ownership", async () => {
    const app = buildApp();
    await app.ready();
    const login = await app.inject({ method: "POST", url: "/auth/login", payload: { handle: "alpha" } });
    const cookie = cookieOf(login);
    expect((await app.inject({ method: "GET", url: "/admin/users", headers: { cookie } })).statusCode).toBe(403);
    expect((await app.inject({ method: "PATCH", url: "/profiles/u-admin", headers: { cookie }, payload: { displayName: "x" } })).statusCode).toBe(403);
    expect((await app.inject({ method: "POST", url: "/auth/logout", headers: { cookie } })).statusCode).toBe(200);
    expect((await app.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(401);
    await app.close();
  });
});
