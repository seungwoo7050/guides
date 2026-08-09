import { StorageReconciler } from "../src/storage/StorageReconciler";
import { ExpoAttachmentFileStore } from "../src/storage/ExpoAttachmentFileStore";
import { DeterministicFileStore } from "../src/storage/testing/DeterministicFileStore";
import {
  DeterministicLocalStore,
  sequentialIds,
} from "../src/storage/testing/DeterministicLocalStore";

async function readyStore() {
  const store = new DeterministicLocalStore();
  await store.ready();
  return store;
}

describe("Stage 02 file ownership and reconciliation", () => {
  it.each([
    "file:///sandbox/outside.bin",
    "file:///sandbox/field-notes/owned/",
    "file:///sandbox/field-notes/owned/.",
    "file:///sandbox/field-notes/owned/..",
    "file:///sandbox/field-notes/owned/../outside.bin",
    "file:///sandbox/field-notes/owned/%2e%2e%2foutside.bin",
    "file:///sandbox/field-notes/owned/subdirectory/file.bin",
    "file:///sandbox/field-notes/owned/subdirectory\\file.bin",
    "file:///sandbox/field-notes/owned/safe.bin?outside=true",
    "file:///sandbox/field-notes/owned/safe.bin#fragment",
  ])("rejects outside or non-flat delete target before touching the filesystem: %s", async (uri) => {
    const files = new ExpoAttachmentFileStore({
      documentDirectory: "file:///sandbox/",
    });
    await expect(files.remove(uri)).rejects.toThrow(/app-owned|outside/);
  });

  it("persists only verified app-owned identity and deduplicates the same result", async () => {
    const store = await readyStore();
    const files = new DeterministicFileStore(sequentialIds());
    files.addTemporary("provider://picked/photo", "non-sensitive fixture bytes");
    const owned = await files.takeOwnership("provider://picked/photo");
    const input = {
      id: "attachment-fixed",
      recordId: "forest-edge",
      localUri: owned.ownedUri,
      checksum: owned.checksum,
      byteSize: owned.byteSize,
      mimeType: "application/octet-stream",
    } as const;
    const first = await store.attachOwnedFile(input);
    const duplicate = await store.attachOwnedFile(input);

    expect(first).toEqual(duplicate);
    expect(first.localUri).toMatch(/^file:\/\/field-notes\/owned\//);
    expect(first.localUri).not.toContain("provider://");
    expect((await store.snapshot()).attachments).toEqual([first]);
  });

  it("leaves no row for a partial copy and startup cleanup removes staging", async () => {
    const store = await readyStore();
    const files = new DeterministicFileStore();
    files.addTemporary("provider://partial", "0123456789");
    files.failNextCopyPartially();
    await expect(files.takeOwnership("provider://partial")).rejects.toThrow("partial copy");
    expect((await store.snapshot()).attachments).toEqual([]);

    const report = await new StorageReconciler(store, files).reconcile();
    expect(report.stagingFilesRemoved).toBe(1);
    expect(report.failures).toEqual([]);
  });

  it("identifies and removes an owned orphan after metadata transaction rollback", async () => {
    const store = await readyStore();
    const files = new DeterministicFileStore();
    files.addTemporary("provider://orphan", "owned before database failure");
    const owned = await files.takeOwnership("provider://orphan");
    store.failNextAt("after-attachment-write");
    await expect(
      store.attachOwnedFile({
        id: "attachment-orphan",
        recordId: "forest-edge",
        localUri: owned.ownedUri,
        checksum: owned.checksum,
        byteSize: owned.byteSize,
        mimeType: "application/octet-stream",
      }),
    ).rejects.toThrow("after-attachment-write");
    expect((await store.snapshot()).attachments).toEqual([]);
    expect(files.ownedUris()).toEqual([owned.ownedUri]);

    const report = await new StorageReconciler(store, files).reconcile();
    expect(report.removedOrphanUris).toEqual([owned.ownedUri]);
    expect(files.ownedUris()).toEqual([]);
  });

  it("marks a row missing when bytes disappear outside the database", async () => {
    const store = await readyStore();
    const files = new DeterministicFileStore();
    files.addTemporary("provider://missing", "bytes later lost");
    const owned = await files.takeOwnership("provider://missing");
    await store.attachOwnedFile({
      id: "attachment-missing",
      recordId: "forest-edge",
      localUri: owned.ownedUri,
      checksum: owned.checksum,
      byteSize: owned.byteSize,
      mimeType: "application/octet-stream",
    });
    files.removeOutsideTheAppForTest(owned.ownedUri);

    const report = await new StorageReconciler(store, files).reconcile();
    expect(report.missingAttachmentIds).toEqual(["attachment-missing"]);
    expect((await store.listAttachments("forest-edge"))[0]?.state).toBe(
      "missing-local-file",
    );
  });

  it("keeps a tombstone durable while converging attachment cleanup separately", async () => {
    const store = await readyStore();
    const files = new DeterministicFileStore();
    files.addTemporary("provider://delete", "delete cleanup bytes");
    const owned = await files.takeOwnership("provider://delete");
    await store.attachOwnedFile({
      id: "attachment-delete",
      recordId: "forest-edge",
      localUri: owned.ownedUri,
      checksum: owned.checksum,
      byteSize: owned.byteSize,
      mimeType: "application/octet-stream",
    });
    const record = await store.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    await store.deleteWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
    });
    expect((await store.listAttachments(record.id))[0]?.state).toBe("cleanup-pending");

    const report = await new StorageReconciler(store, files).reconcile();
    expect(report.removedAttachmentIds).toEqual(["attachment-delete"]);
    expect((await store.listAttachments(record.id))[0]?.state).toBe("removed");
    const snapshot = await store.snapshot();
    expect(snapshot.records.find((item) => item.id === record.id)?.deletedAtLocal).toEqual(
      expect.any(String),
    );
    expect(snapshot.outbox.at(-1)?.operation).toBe("delete");
  });
});
