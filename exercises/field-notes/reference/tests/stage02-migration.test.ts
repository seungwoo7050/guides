import {
  CURRENT_SCHEMA_VERSION,
  V1_FIXTURE_RECORDS,
} from "../src/storage/migrations";
import {
  DeterministicDatabaseBacking,
  DeterministicLocalStore,
} from "../src/storage/testing/DeterministicLocalStore";

describe("Stage 02 v1 forward migration", () => {
  it("preserves ids and payload, assigns honest defaults, and fabricates no command", async () => {
    const backing = DeterministicDatabaseBacking.v1();
    const store = new DeterministicLocalStore(backing);
    await store.ready();
    const snapshot = await store.snapshot();

    expect(snapshot.schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
    expect(snapshot.records).toHaveLength(V1_FIXTURE_RECORDS.length);
    expect(snapshot.records.map((record) => record.id).sort()).toEqual(
      V1_FIXTURE_RECORDS.map((record) => record.id).sort(),
    );
    expect(snapshot.records.find((record) => record.id === "legacy-null-notes")).toMatchObject({
      notes: "",
      status: "open",
      localRevision: 1,
      remoteVersion: null,
      syncState: "local-only",
    });
    expect(
      snapshot.records.find((record) => record.id === "legacy-long-unicode")?.notes.length,
    ).toBeGreaterThan(500);
    expect(snapshot.outbox).toEqual([]);
    expect(snapshot.migrationHistory).toEqual([
      { fromVersion: 0, toVersion: 1 },
      { fromVersion: 1, toVersion: 2 },
      { fromVersion: 2, toVersion: 3 },
      { fromVersion: 3, toVersion: 4 },
      { fromVersion: 4, toVersion: 5 },
      { fromVersion: 5, toVersion: 6 },
    ]);
  });

  it("does not advance or erase v1 when migration fails, and is retryable", async () => {
    const backing = DeterministicDatabaseBacking.v1();
    const failing = new DeterministicLocalStore(backing);
    failing.failNextAt("migration-to-2");
    await expect(failing.ready()).rejects.toThrow("migration-to-2");

    expect(backing.state.schemaVersion).toBe(1);
    expect(backing.state.legacyRecords).toEqual(
      V1_FIXTURE_RECORDS.map((record) => ({ ...record })),
    );
    expect(backing.state.records.size).toBe(0);
    expect(backing.state.outbox.size).toBe(0);

    const retry = new DeterministicLocalStore(backing);
    await expect(retry.ready()).resolves.toBeUndefined();
    expect((await retry.snapshot()).schemaVersion).toBe(CURRENT_SCHEMA_VERSION);
  });
});
