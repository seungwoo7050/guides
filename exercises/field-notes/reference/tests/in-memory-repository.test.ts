import { InMemoryRecordRepository, RevisionMismatchError } from "../src/data/InMemoryRecordRepository";

describe("Stage 01 in-memory repository", () => {
  it("returns copies so a screen cannot mutate the repository by reference", async () => {
    const repository = new InMemoryRecordRepository();
    const record = await repository.get("forest-edge");
    expect(record).not.toBeNull();
    if (record === null) return;
    record.title = "accidental mutation";
    await expect(repository.get("forest-edge")).resolves.toMatchObject({
      title: "숲 가장자리 토양 상태",
    });
  });

  it("increments a local revision but honestly remains memory-only", async () => {
    const repository = new InMemoryRecordRepository();
    const current = await repository.get("forest-edge");
    if (current === null) throw new Error("fixture missing");
    const saved = await repository.saveInMemory({
      id: current.id,
      expectedLocalRevision: current.localRevision,
      payload: {
        title: "수정한 제목",
        notes: current.notes,
        status: current.status,
        observedAt: current.observedAt,
      },
    });
    expect(saved).toMatchObject({
      localRevision: current.localRevision + 1,
      remoteVersion: null,
      syncState: "local-only",
    });
  });

  it("rejects a stale editor rather than silently overwriting newer memory", async () => {
    const repository = new InMemoryRecordRepository();
    const current = await repository.get("harbor-light");
    if (current === null) throw new Error("fixture missing");
    const input = {
      id: current.id,
      expectedLocalRevision: current.localRevision,
      payload: {
        title: current.title,
        notes: "first editor",
        status: current.status,
        observedAt: current.observedAt,
      },
    } as const;
    await repository.saveInMemory(input);
    await expect(repository.saveInMemory(input)).rejects.toBeInstanceOf(
      RevisionMismatchError,
    );
  });
});

