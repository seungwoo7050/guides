import { beforeEach, describe, expect, it } from "vitest";
import { MemoryRepository } from "./index";

describe("메모리 저장소", () => {
  let repo: MemoryRepository;
  beforeEach(async () => {
    repo = new MemoryRepository();
    await repo.seed();
  });

  it("읽기 전용 구성원의 쓰기를 거부합니다", async () => {
    const viewer = await repo.upsertUser({ handle: "viewer", displayName: "읽기 전용 사용자" });
    const [board] = await repo.listBoards(viewer.id);
    await expect(repo.createItem(board!.id, viewer.id, {
      kind: "note",
      content: "허용되지 않는 변경",
      x: 10,
      y: 10
    })).rejects.toThrow("read_only");
  });

  it("이동 완료와 활동 이벤트를 함께 기록합니다", async () => {
    const owner = await repo.upsertUser({ handle: "owner", displayName: "보드 소유자" });
    const [board] = await repo.listBoards(owner.id);
    const snapshot = await repo.getBoardSnapshot(board!.id, owner.id);
    const item = snapshot!.items[0]!;
    const result = await repo.persistItemMove(board!.id, owner.id, item.id, 300, 240, item.version);
    expect(result?.item.x).toBe(300);
    expect((await repo.listBoardEvents(board!.id, owner.id))[0]?.eventType).toBe("item.move");
  });
});
