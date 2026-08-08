import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createMemoryRepository, type AppRepository } from "@board/db";
import { buildApp } from "./app";

function cookieOf(headers: Record<string, string | string[] | number | undefined>) {
  const value = headers["set-cookie"];
  return String(Array.isArray(value) ? value[0] : value).split(";")[0];
}

describe("HTTP API", () => {
  let repo: AppRepository;
  let app: ReturnType<typeof buildApp>;

  beforeEach(async () => {
    repo = createMemoryRepository();
    await repo.seed();
    app = buildApp(repo);
    await app.ready();
  });
  afterEach(async () => app.close());

  it("로그인한 사용자가 보드를 만들고 조회합니다", async () => {
    const login = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { handle: "maker", displayName: "만든 사람" }
    });
    const cookie = cookieOf(login.headers);
    const created = await app.inject({
      method: "POST",
      url: "/boards",
      headers: { cookie },
      payload: { title: "새 협업 보드" }
    });
    expect(created.statusCode).toBe(201);
    const listed = await app.inject({ method: "GET", url: "/boards", headers: { cookie } });
    expect(listed.json().boards).toHaveLength(1);
  });

  it("일반 사용자의 관리 API 접근을 거부합니다", async () => {
    const login = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { handle: "member", displayName: "구성원" }
    });
    const response = await app.inject({
      method: "GET",
      url: "/admin/users",
      headers: { cookie: cookieOf(login.headers) }
    });
    expect(response.statusCode).toBe(403);
  });

  it("세션이 없는 요청과 권한이 없는 요청을 구분합니다", async () => {
    const anonymous = await app.inject({ method: "GET", url: "/boards" });
    expect(anonymous.statusCode).toBe(401);
    expect(anonymous.json()).toMatchObject({ code: "unauthorized" });

    const login = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { handle: "member", displayName: "구성원" }
    });
    const forbidden = await app.inject({
      method: "GET",
      url: "/admin/actions",
      headers: { cookie: cookieOf(login.headers) }
    });
    expect(forbidden.statusCode).toBe(403);
    expect(forbidden.json()).toMatchObject({ code: "forbidden" });
  });

  it("허용하지 않은 Origin의 상태 변경 요청을 거부합니다", async () => {
    const response = await app.inject({
      method: "POST",
      url: "/auth/login",
      headers: { origin: "https://attacker.invalid" },
      payload: { handle: "member", displayName: "구성원" }
    });
    expect(response.statusCode).toBe(403);
    expect(response.json()).toMatchObject({ code: "origin_forbidden" });
  });

  it("로그아웃하면 서버 세션과 브라우저 쿠키를 함께 폐기합니다", async () => {
    const login = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { handle: "member", displayName: "구성원" }
    });
    const cookie = cookieOf(login.headers);
    const logout = await app.inject({ method: "POST", url: "/auth/logout", headers: { cookie } });
    expect(logout.statusCode).toBe(200);
    expect(String(logout.headers["set-cookie"])).toContain("board_session=;");
    expect((await app.inject({ method: "GET", url: "/me", headers: { cookie } })).statusCode).toBe(401);
  });
});
