import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createPostgresRepository } from "./postgres";

const suite = process.env.DATABASE_URL ? describe : describe.skip;
suite("PostgreSQL 저장소", () => {
  const repo = createPostgresRepository(process.env.DATABASE_URL!);
  beforeAll(async () => repo.seed());
  afterAll(async () => repo.close());

  it("세션과 보드를 저장합니다", async () => {
    const user = await repo.upsertUser({ handle: `pg-${Date.now()}`, displayName: "DB 사용자" });
    const token = await repo.createSession(user.id);
    expect((await repo.getSessionUser(token))?.id).toBe(user.id);
    const board = await repo.createBoard(user.id, "DB 보드");
    expect((await repo.listBoards(user.id))[0]?.id).toBe(board.id);
  });
});
