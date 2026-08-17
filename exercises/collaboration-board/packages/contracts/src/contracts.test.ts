import { describe, expect, it } from "vitest";

import { ClientEventSchema, LoginRequestSchema } from "./index";

describe("shared contracts", () => {
  it("normalizes valid login input and rejects invalid handles", () => {
    expect(LoginRequestSchema.parse({ handle: "owner", displayName: " Owner " })).toEqual({
      handle: "owner",
      displayName: "Owner"
    });
    expect(LoginRequestSchema.safeParse({ handle: "Owner!", displayName: "Owner" }).success).toBe(false);
  });

  it("rejects a persistent item mutation without baseVersion", () => {
    expect(ClientEventSchema.safeParse({
      type: "item.update",
      boardId: "00000000-0000-4000-8000-000000000001",
      itemId: "00000000-0000-4000-8000-000000000002",
      content: "changed"
    }).success).toBe(false);
  });

  it("rejects realtime coordinates outside the logical board", () => {
    expect(ClientEventSchema.safeParse({
      type: "cursor.move",
      boardId: "00000000-0000-4000-8000-000000000001",
      x: 1_601,
      y: 20
    }).success).toBe(false);
  });
});
