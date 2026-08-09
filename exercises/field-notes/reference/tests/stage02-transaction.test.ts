import type { RecordPayload } from "@field-notes/shared";
import { LocalRevisionMismatchError } from "../src/storage/localMutation";
import {
  DeterministicDatabaseBacking,
  DeterministicLocalStore,
  sequentialIds,
} from "../src/storage/testing/DeterministicLocalStore";

const UPDATED_PAYLOAD: Readonly<RecordPayload> = {
  title: "오프라인에서 수정한 관찰",
  notes: "remote 응답을 기다리지 않고 local commit을 표시한다.",
  status: "open",
  observedAt: "2026-08-09T13:00:00.000Z",
};

function makeStore(backing = new DeterministicDatabaseBacking()) {
  let tick = 0;
  return new DeterministicLocalStore(
    backing,
    { now: () => `2026-08-09T13:00:0${tick++}.000Z` },
    sequentialIds(),
  );
}

describe("Stage 02 record + outbox transaction", () => {
  it("commits the record revision and immutable command snapshot together", async () => {
    const store = makeStore();
    await store.ready();
    const before = await store.get("forest-edge");
    if (before === null) throw new Error("migrated fixture missing");

    const payload = { ...UPDATED_PAYLOAD };
    const commit = store.saveWithCommand({
      id: before.id,
      expectedLocalRevision: before.localRevision,
      payload,
    });
    payload.title = "caller mutated object after save call";
    const result = await commit;

    const snapshot = await store.snapshot();
    expect(result.record).toMatchObject({ localRevision: 2, syncState: "pending" });
    expect(snapshot.records.find((record) => record.id === before.id)).toMatchObject({
      title: "오프라인에서 수정한 관찰",
      localRevision: 2,
      remoteVersion: null,
      syncState: "pending",
    });
    expect(snapshot.outbox).toHaveLength(1);
    expect(snapshot.outbox[0]).toMatchObject({
      commandId: result.command.commandId,
      recordId: before.id,
      operation: "upsert",
      localRevision: 2,
      baseVersion: null,
      state: "pending",
      attemptCount: 0,
      payload: { title: "오프라인에서 수정한 관찰" },
    });
  });

  it("rolls back both sides when a fault occurs after the record write", async () => {
    const store = makeStore();
    await store.ready();
    const before = await store.snapshot();
    const record = await store.get("harbor-light");
    if (record === null) throw new Error("fixture missing");
    store.failNextAt("after-record-write");

    await expect(
      store.saveWithCommand({
        id: record.id,
        expectedLocalRevision: record.localRevision,
        payload: { ...UPDATED_PAYLOAD, title: "rollback candidate" },
      }),
    ).rejects.toThrow("injected fault");
    expect(await store.snapshot()).toEqual(before);
  });

  it("serializes duplicate saves so only one expected revision can commit", async () => {
    const store = makeStore();
    await store.ready();
    const record = await store.get("ridge-marker");
    if (record === null) throw new Error("fixture missing");
    const input = {
      id: record.id,
      expectedLocalRevision: record.localRevision,
      payload: { ...UPDATED_PAYLOAD, title: "double tap" },
    };
    const [first, second] = await Promise.allSettled([
      store.saveWithCommand(input),
      store.saveWithCommand(input),
    ]);
    expect(first.status).toBe("fulfilled");
    expect(second.status).toBe("rejected");
    if (second.status === "rejected") {
      expect(second.reason).toBeInstanceOf(LocalRevisionMismatchError);
    }
    const snapshot = await store.snapshot();
    expect(snapshot.outbox.filter((entry) => entry.recordId === record.id)).toHaveLength(1);
    expect(snapshot.records.find((item) => item.id === record.id)?.localRevision).toBe(2);
  });

  it("restores the committed record and command from the same backing after reopen", async () => {
    const backing = new DeterministicDatabaseBacking();
    const firstProcess = makeStore(backing);
    await firstProcess.ready();
    const record = await firstProcess.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    await firstProcess.saveWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
      payload: { ...UPDATED_PAYLOAD, title: "restart snapshot" },
    });

    const secondProcess = makeStore(backing);
    const reopened = await secondProcess.snapshot();
    expect(reopened.records.find((item) => item.id === record.id)).toMatchObject({
      title: "restart snapshot",
      localRevision: 2,
      syncState: "pending",
    });
    expect(reopened.outbox).toHaveLength(1);
    expect(reopened.outbox[0]?.payload).toMatchObject({ title: "restart snapshot" });
  });

  it("commits a tombstone and delete command while hiding the record from normal list", async () => {
    const store = makeStore();
    await store.ready();
    const record = await store.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    const deleted = await store.deleteWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
    });

    expect(await store.get(record.id)).toBeNull();
    expect((await store.list()).some((item) => item.id === record.id)).toBe(false);
    const snapshot = await store.snapshot();
    expect(snapshot.records.find((item) => item.id === record.id)).toMatchObject({
      localRevision: 2,
      syncState: "pending",
      deletedAtLocal: expect.any(String),
    });
    expect(snapshot.outbox).toContainEqual(
      expect.objectContaining({
        commandId: deleted.command.commandId,
        operation: "delete",
        payload: null,
        localRevision: 2,
      }),
    );
  });
});
