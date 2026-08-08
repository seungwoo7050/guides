import { describe, expect, it } from "vitest";
import { buildApp } from "./app";
import { MemoryMemoRepository } from "./repository";

describe("memo API", () => {
  it("validates, creates and rejects duplicates", async () => {
    const app = buildApp(new MemoryMemoRepository());
    await app.ready();
    const invalid = await app.inject({ method: "POST", url: "/memos", payload: { title: "" } });
    expect(invalid.statusCode).toBe(400);
    const created = await app.inject({ method: "POST", url: "/memos", payload: { title: "one", body: "body" } });
    expect(created.statusCode).toBe(201);
    const duplicate = await app.inject({ method: "POST", url: "/memos", payload: { title: "one" } });
    expect(duplicate.statusCode).toBe(409);
    await app.close();
  });
});
