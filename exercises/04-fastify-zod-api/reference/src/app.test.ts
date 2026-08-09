import { describe, expect, it } from "vitest";
import { buildApp } from "./app";
import { MemoryMemoRepository } from "./repository";

describe("memo API", () => {
  it("validates input, creates a memo and rejects duplicates", async () => {
    const app = buildApp(new MemoryMemoRepository());
    await app.ready();
    const invalid = await app.inject({ method: "POST", url: "/memos", payload: { title: "" } });
    expect(invalid.statusCode).toBe(400);
    expect(invalid.json()).toEqual({
      code: "invalid_request",
      message: "요청이 올바르지 않습니다."
    });
    const malformed = await app.inject({
      method: "POST",
      url: "/memos",
      headers: { "content-type": "application/json" },
      payload: "{"
    });
    expect(malformed.statusCode).toBe(400);
    expect(malformed.json()).toEqual({
      code: "invalid_request",
      message: "요청이 올바르지 않습니다."
    });
    expect(invalid.body + malformed.body).not.toContain("issues");
    const created = await app.inject({ method: "POST", url: "/memos", payload: { title: "one", body: "body" } });
    expect(created.statusCode).toBe(201);
    const duplicate = await app.inject({ method: "POST", url: "/memos", payload: { title: "one" } });
    expect(duplicate.statusCode).toBe(409);
    expect(duplicate.json()).toEqual({
      code: "title_taken",
      message: "title already exists"
    });
    await app.close();
  });

  it("returns a stable 404 contract for a missing memo", async () => {
    const app = buildApp(new MemoryMemoRepository());
    await app.ready();
    const response = await app.inject({ method: "GET", url: "/memos/missing" });
    expect(response.statusCode).toBe(404);
    expect(response.json()).toEqual({ code: "not_found", message: "메모를 찾을 수 없습니다." });
    await app.close();
  });

  it("maps unexpected failures without leaking internal details", async () => {
    class FailingMemoRepository extends MemoryMemoRepository {
      override async list(): Promise<never> {
        throw new Error("password_hash column is unavailable");
      }
    }

    const app = buildApp(new FailingMemoRepository());
    await app.ready();
    const response = await app.inject({ method: "GET", url: "/memos" });
    expect(response.statusCode).toBe(500);
    expect(response.json()).toEqual({
      code: "internal_error",
      message: "요청을 처리하지 못했습니다."
    });
    expect(response.body).not.toContain("password_hash");
    await app.close();
  });
});
