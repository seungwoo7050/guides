import type { Clock, RecordPayload } from "@field-notes/shared";
import { SerializedForegroundPipeline } from "../src/application/SerializedForegroundPipeline";
import { DeviceFeatureCoordinator } from "../src/device/DeviceFeatureCoordinator";
import {
  DeterministicCameraAdapter,
  DeterministicLocationAdapter,
  DeterministicPendingMediaAdapter,
  DeterministicPhotoPickerAdapter,
} from "../src/device/testing/DeterministicDeviceAdapters";
import { StorageReconciler } from "../src/storage/StorageReconciler";
import { DeterministicFileStore } from "../src/storage/testing/DeterministicFileStore";
import {
  DeterministicLocalStore,
  sequentialIds,
} from "../src/storage/testing/DeterministicLocalStore";

const TEXT_UPDATE: RecordPayload = {
  title: "권한과 무관하게 보존할 text",
  notes: "optional capability failure must not block this commit",
  status: "open",
  observedAt: "2026-08-09T15:10:00.000Z",
};

class MutableClock implements Clock {
  public value = "2026-08-09T15:00:00.000Z";
  public now(): string {
    return this.value;
  }
}

async function setup() {
  const store = new DeterministicLocalStore();
  await store.ready();
  const ids = sequentialIds();
  const files = new DeterministicFileStore(ids);
  const camera = new DeterministicCameraAdapter();
  const picker = new DeterministicPhotoPickerAdapter();
  const location = new DeterministicLocationAdapter();
  const pending = new DeterministicPendingMediaAdapter();
  const clock = new MutableClock();
  const coordinator = new DeviceFeatureCoordinator(
    camera,
    picker,
    location,
    pending,
    store,
    files,
    clock,
    ids,
  );
  return { store, files, camera, picker, location, pending, clock, coordinator };
}

describe("Stage 03 media lifecycle", () => {
  it("inspects startup state without requesting any permission", async () => {
    const { coordinator, camera, picker, location } = await setup();
    const snapshot = await coordinator.inspectCapabilities();
    expect(snapshot.photoPicker.permission).toEqual({ kind: "not-required" });
    expect(camera.permissionRequests).toBe(0);
    expect(picker.permissionRequests).toBe(0);
    expect(location.permissionRequests).toBe(0);
  });

  it("routes a selected photo through one owned-file + atomic metadata completion", async () => {
    const { coordinator, files, picker, store } = await setup();
    files.addTemporary("provider://one-selected-item", "deterministic image bytes");
    picker.selectionResult = {
      kind: "acquired",
      temporaryUri: "provider://one-selected-item",
      mimeType: "image/jpeg",
    };

    const result = await coordinator.pickPhoto("forest-edge");
    expect(result).toEqual(
      expect.objectContaining({ kind: "attached", recovered: false }),
    );
    expect(picker.permissionRequests).toBe(0);
    const snapshot = await store.snapshot();
    expect(snapshot.attachments).toHaveLength(1);
    expect(snapshot.attachments[0]).toMatchObject({
      recordId: "forest-edge",
      state: "local-ready",
      mimeType: "image/jpeg",
    });
    expect(snapshot.attachments[0]?.localUri).not.toContain("provider://");
    expect(snapshot.externalMediaOperations).toContainEqual(
      expect.objectContaining({ state: "completed", attachmentId: snapshot.attachments[0]?.id }),
    );
  });

  it("treats camera and picker cancel as normal without attachment or record command", async () => {
    const { coordinator, camera, picker, store } = await setup();
    camera.captureResult = { kind: "cancelled" };
    picker.selectionResult = { kind: "cancelled" };

    expect(await coordinator.capturePhoto("forest-edge")).toEqual({ kind: "cancelled" });
    expect(await coordinator.pickPhoto("forest-edge")).toEqual({ kind: "cancelled" });
    const snapshot = await store.snapshot();
    expect(snapshot.attachments).toEqual([]);
    expect(snapshot.outbox).toEqual([]);
    expect(snapshot.externalMediaOperations.map((operation) => operation.state)).toEqual([
      "cancelled",
      "cancelled",
    ]);
  });

  it("does not prompt or launch unavailable camera and preserves text-only save", async () => {
    const { coordinator, camera, store } = await setup();
    camera.availabilityState = { kind: "unavailable", reason: "no camera hardware" };
    const outcome = await coordinator.capturePhoto("forest-edge");
    expect(outcome).toEqual(expect.objectContaining({ kind: "unavailable" }));
    expect(camera.permissionQueries).toBe(0);
    expect(camera.permissionRequests).toBe(0);
    expect(camera.captures).toBe(0);

    const record = await store.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    await store.saveWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
      payload: TEXT_UPDATE,
    });
    expect(await store.get(record.id)).toMatchObject({ title: TEXT_UPDATE.title });
  });

  it.each([
    { kind: "denied", canAskAgain: false } as const,
    { kind: "restricted", reason: "device policy" } as const,
  ])("does not repeat camera prompt for $kind and keeps alternatives", async (permission) => {
    const { coordinator, camera, store } = await setup();
    camera.permissionState = permission;
    const outcome = await coordinator.capturePhoto("forest-edge");
    expect(outcome).toEqual({ kind: "denied", permission });
    expect(camera.permissionRequests).toBe(0);
    expect(camera.captures).toBe(0);
    expect((await store.snapshot()).externalMediaOperations).toEqual([]);
  });

  it("records revocation between check and use as failed without losing record", async () => {
    const { coordinator, camera, store } = await setup();
    camera.captureResult = {
      kind: "failed",
      code: "permission-revoked",
      reason: "revoked before native launch",
    };
    expect(await coordinator.capturePhoto("forest-edge")).toEqual(
      expect.objectContaining({ kind: "failed", code: "permission-revoked" }),
    );
    const snapshot = await store.snapshot();
    expect(snapshot.attachments).toEqual([]);
    expect(snapshot.records.find((record) => record.id === "forest-edge")).toBeDefined();
    expect(snapshot.externalMediaOperations[0]).toMatchObject({ state: "failed" });
  });

  it("terminalizes a thrown external UI operation and permits an explicit retry", async () => {
    const { coordinator, camera, store } = await setup();
    camera.capture = async () => {
      throw new Error("native activity disappeared");
    };
    expect(await coordinator.capturePhoto("forest-edge")).toEqual(
      expect.objectContaining({ kind: "interrupted" }),
    );
    expect((await store.snapshot()).externalMediaOperations.at(-1)).toMatchObject({
      state: "interrupted",
      failureReason: "external-ui-threw",
    });

    camera.capture = async () => ({ kind: "cancelled" });
    expect(await coordinator.capturePhoto("forest-edge")).toEqual({ kind: "cancelled" });
    expect((await store.snapshot()).externalMediaOperations.map((operation) => operation.state))
      .toEqual(["interrupted", "cancelled"]);
  });

  it("cleans partial staging and commits no metadata when provider copy fails", async () => {
    const { coordinator, files, picker, store } = await setup();
    files.addTemporary("provider://partial", "0123456789");
    files.failNextCopyPartially();
    picker.selectionResult = {
      kind: "acquired",
      temporaryUri: "provider://partial",
      mimeType: "image/png",
    };
    expect(await coordinator.pickPhoto("forest-edge")).toEqual(
      expect.objectContaining({ kind: "failed", code: "copy-failed" }),
    );
    expect((await store.snapshot()).attachments).toEqual([]);
    expect((await new StorageReconciler(store, files).reconcile()).stagingFilesRemoved).toBe(0);
  });

  it.each([
    { mimeType: "application/pdf", expectedCode: "unsupported-media-type" },
    { mimeType: "image/jpeg", expectedCode: "copy-failed", contents: "" },
  ])("rejects invalid media before metadata commit: $expectedCode", async ({ mimeType, expectedCode, contents = "image bytes" }) => {
    const { coordinator, files, picker, store } = await setup();
    files.addTemporary("provider://invalid-media", contents);
    picker.selectionResult = {
      kind: "acquired",
      temporaryUri: "provider://invalid-media",
      mimeType,
    };
    expect(await coordinator.pickPhoto("forest-edge")).toEqual(
      expect.objectContaining({ kind: "failed", code: expectedCode }),
    );
    expect((await store.snapshot()).attachments).toEqual([]);
    expect(files.ownedUris()).toEqual([]);
  });

  it("removes an oversized owned copy and commits no attachment row", async () => {
    const { coordinator, files, picker, store } = await setup();
    files.addTemporary("provider://large", "small deterministic bytes");
    files.reportNextOwnedByteSize(20 * 1024 * 1024 + 1);
    picker.selectionResult = {
      kind: "acquired",
      temporaryUri: "provider://large",
      mimeType: "image/jpeg",
    };
    expect(await coordinator.pickPhoto("forest-edge")).toEqual(
      expect.objectContaining({ kind: "failed", code: "file-too-large" }),
    );
    expect((await store.snapshot()).attachments).toEqual([]);
    expect(files.ownedUris()).toEqual([]);
  });

  it("re-queries a revoked permission on active without automatically relaunching", async () => {
    const { coordinator, camera } = await setup();
    expect((await coordinator.inspectCapabilities()).camera.permission).toEqual({
      kind: "granted",
    });
    camera.permissionState = { kind: "denied", canAskAgain: false };
    expect((await coordinator.inspectCapabilities()).camera.permission).toEqual({
      kind: "denied",
      canAskAgain: false,
    });
    expect(camera.permissionRequests).toBe(0);
    expect(camera.captures).toBe(0);
  });

  it("maps a thrown location adapter to failed and allows a later retry", async () => {
    const { coordinator, location } = await setup();
    location.current = async () => {
      throw new Error("native location bridge unavailable");
    };
    await expect(coordinator.measureLocation()).resolves.toEqual(
      expect.objectContaining({ kind: "failed" }),
    );
    location.current = async () => ({
      kind: "measured",
      latitude: 37.5,
      longitude: 127,
      accuracyMeters: 8,
      measuredAt: "2026-08-09T15:00:00.000Z",
    });
    await expect(coordinator.measureLocation()).resolves.toEqual(
      expect.objectContaining({ kind: "preview" }),
    );
  });

  it("leaves a DB-fault orphan for Stage 02 reconciliation while preserving the record", async () => {
    const { coordinator, files, picker, store } = await setup();
    files.addTemporary("provider://db-fault", "owned before metadata rollback");
    picker.selectionResult = {
      kind: "acquired",
      temporaryUri: "provider://db-fault",
      mimeType: "image/jpeg",
    };
    store.failNextAt("after-attachment-write");
    expect(await coordinator.pickPhoto("forest-edge")).toEqual(
      expect.objectContaining({ kind: "failed", code: "metadata-commit-failed" }),
    );
    expect((await store.snapshot()).attachments).toEqual([]);
    expect(files.ownedUris()).toHaveLength(1);
    expect(await store.get("forest-edge")).not.toBeNull();

    const report = await new StorageReconciler(store, files).reconcile();
    expect(report.removedOrphanUris).toHaveLength(1);
    expect(files.ownedUris()).toEqual([]);
  });

  it("serializes foreground reconciliation behind owned-file metadata completion", async () => {
    const pipeline = new SerializedForegroundPipeline();
    const owned = new Set<string>();
    const metadata = new Set<string>();
    let releaseCommit: (() => void) | undefined;
    const waitForCommit = new Promise<void>((resolve) => {
      releaseCommit = resolve;
    });
    const acquire = pipeline.run(async () => {
      owned.add("file://field-notes/owned/serialized.bin");
      await waitForCommit;
      metadata.add("file://field-notes/owned/serialized.bin");
    });
    await Promise.resolve();
    const reconcile = pipeline.run(async () => {
      for (const uri of owned) {
        if (!metadata.has(uri)) owned.delete(uri);
      }
    });
    await Promise.resolve();
    expect(owned).toEqual(new Set(["file://field-notes/owned/serialized.bin"]));
    releaseCommit?.();
    await Promise.all([acquire, reconcile]);
    expect(owned).toEqual(new Set(["file://field-notes/owned/serialized.bin"]));
    expect(metadata).toEqual(new Set(["file://field-notes/owned/serialized.bin"]));
  });

  it("recovers an Android pending result once and rejects duplicate delivery", async () => {
    const { coordinator, files, pending, store } = await setup();
    await store.beginExternalMediaOperation({
      operationId: "media-operation-recovery",
      recordId: "forest-edge",
      source: "photo-picker",
      createdAt: "2026-08-09T14:59:00.000Z",
      expiresAt: "2026-08-09T15:14:00.000Z",
    });
    files.addTemporary("provider://recovered", "recovered image bytes");
    pending.result = {
      kind: "acquired",
      temporaryUri: "provider://recovered",
      mimeType: "image/jpeg",
    };

    expect(await coordinator.recoverPendingMedia()).toEqual(
      expect.objectContaining({ kind: "attached", recovered: true }),
    );
    expect(await coordinator.recoverPendingMedia()).toEqual({ kind: "duplicate" });
    expect((await store.snapshot()).attachments).toHaveLength(1);
    expect(files.ownedUris()).toHaveLength(1);
  });

  it("expires a stale operation without consuming a platform result", async () => {
    const { coordinator, pending, store } = await setup();
    await store.beginExternalMediaOperation({
      operationId: "media-operation-expired",
      recordId: "forest-edge",
      source: "camera",
      createdAt: "2026-08-09T14:00:00.000Z",
      expiresAt: "2026-08-09T14:15:00.000Z",
    });
    pending.result = { kind: "cancelled" };

    expect(await coordinator.recoverPendingMedia()).toEqual(
      expect.objectContaining({ kind: "interrupted" }),
    );
    expect(pending.recoveries).toBe(0);
    expect((await store.snapshot()).externalMediaOperations[0]).toMatchObject({
      state: "interrupted",
    });
  });
});
