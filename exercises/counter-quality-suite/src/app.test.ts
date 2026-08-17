import { describe, expect, it } from "vitest";

import { buildApp } from "./app";

// [Implementation 4] Exercise real routing and serialization through app.inject while closing every application resource after each case.
describe("counter HTTP API", () => {
  it("increments, decrements, and resets through HTTP", async () => {
    const app = buildApp();
    await app.ready();
    try {
      expect((await app.inject({ method: "GET", url: "/counter" })).json()).toEqual({ value: 0 });
      expect((await app.inject({ method: "POST", url: "/counter/increment" })).json()).toEqual({ value: 1 });
      expect((await app.inject({ method: "POST", url: "/counter/decrement" })).json()).toEqual({ value: 0 });
      expect((await app.inject({ method: "POST", url: "/counter/decrement" })).json()).toEqual({ value: 0 });
      expect((await app.inject({ method: "POST", url: "/counter/increment" })).json()).toEqual({ value: 1 });
      expect((await app.inject({ method: "POST", url: "/counter/reset" })).json()).toEqual({ value: 0 });
    } finally {
      await app.close();
    }
  });

  it("serves an accessible browser surface", async () => {
    const app = buildApp();
    await app.ready();
    try {
      const response = await app.inject({ method: "GET", url: "/" });
      expect(response.statusCode).toBe(200);
      expect(response.headers["content-type"]).toContain("text/html");
      expect(response.body).toContain('role="status"');
      expect(response.body).toContain("Increment");
    } finally {
      await app.close();
    }
  });
});
