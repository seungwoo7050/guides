import { randomUUID } from "node:crypto";
import { describe, expect, it } from "vitest";
import { ClientEventSchema, LoginRequestSchema, ServerEventSchema } from "./index";

describe("공유 계약", () => {
  it("로그인 입력의 양쪽 공백을 제거합니다", () => {
    expect(LoginRequestSchema.parse({ handle: " alpha ", displayName: " 알파 " }))
      .toEqual({ handle: "alpha", displayName: "알파" });
  });

  it("클라이언트가 보드 버전을 생략한 변경을 거부합니다", () => {
    const result = ClientEventSchema.safeParse({
      type: "item.move",
      boardId: randomUUID(),
      itemId: randomUUID(),
      x: 10,
      y: 20
    });
    expect(result.success).toBe(false);
  });

  it("연결 종료 이벤트를 검증합니다", () => {
    expect(ServerEventSchema.safeParse({
      type: "board.closed",
      boardId: randomUUID(),
      reason: "보드가 보관되었습니다."
    }).success).toBe(true);
  });
});
