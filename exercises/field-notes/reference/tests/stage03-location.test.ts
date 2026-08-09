import type { RecordPayload } from "@field-notes/shared";
import { DeviceFeatureCoordinator } from "../src/device/DeviceFeatureCoordinator";
import {
  deferred,
  DeterministicCameraAdapter,
  DeterministicLocationAdapter,
  DeterministicPendingMediaAdapter,
  DeterministicPhotoPickerAdapter,
} from "../src/device/testing/DeterministicDeviceAdapters";
import { DeterministicFileStore } from "../src/storage/testing/DeterministicFileStore";
import {
  DeterministicLocalStore,
  sequentialIds,
} from "../src/storage/testing/DeterministicLocalStore";

const LOCATION = {
  latitude: 37.501,
  longitude: 127.039,
  accuracyMeters: 850,
  measuredAt: "2026-08-09T15:20:00.000Z",
} as const;

async function setup() {
  const store = new DeterministicLocalStore();
  await store.ready();
  const ids = sequentialIds();
  const location = new DeterministicLocationAdapter();
  const coordinator = new DeviceFeatureCoordinator(
    new DeterministicCameraAdapter(),
    new DeterministicPhotoPickerAdapter(),
    location,
    new DeterministicPendingMediaAdapter(),
    store,
    new DeterministicFileStore(ids),
    { now: () => "2026-08-09T15:00:00.000Z" },
    ids,
  );
  return { store, location, coordinator };
}

function payload(record: NonNullable<Awaited<ReturnType<DeterministicLocalStore["get"]>>>, location?: RecordPayload["location"]): RecordPayload {
  return {
    title: record.title,
    notes: record.notes,
    status: record.status,
    observedAt: record.observedAt,
    location,
  };
}

describe("Stage 03 foreground location", () => {
  it("requests foreground permission only from an explicit measurement action", async () => {
    const { coordinator, location } = await setup();
    location.permissionState = { kind: "not-determined" };
    location.requestedPermission = { kind: "granted" };
    location.measurementResult = { kind: "measured", ...LOCATION };

    await coordinator.inspectCapabilities();
    expect(location.permissionRequests).toBe(0);
    expect(await coordinator.measureLocation()).toEqual({
      kind: "preview",
      location: LOCATION,
    });
    expect(location.permissionRequests).toBe(1);
    expect(location.measurements).toBe(1);
  });

  it("keeps a valid or low-accuracy measurement memory-only until user includes it", async () => {
    const { coordinator, location, store } = await setup();
    location.measurementResult = { kind: "measured", ...LOCATION };
    const before = await store.snapshot();
    const outcome = await coordinator.measureLocation();
    expect(outcome).toEqual({ kind: "preview", location: LOCATION });
    expect(await store.snapshot()).toEqual(before);

    if (outcome.kind !== "preview") throw new Error("preview missing");
    const record = await store.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    await store.saveWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
      payload: payload(record, outcome.location),
    });
    const after = await store.snapshot();
    expect(after.records.find((item) => item.id === record.id)?.location).toEqual(LOCATION);
    expect(after.outbox).toHaveLength(1);
    expect(after.outbox[0]?.payload?.location).toEqual(LOCATION);
  });

  it("denial and measurement failure still allow a location-free text commit", async () => {
    const { coordinator, location, store } = await setup();
    location.permissionState = { kind: "denied", canAskAgain: false };
    expect(await coordinator.measureLocation()).toEqual({
      kind: "denied",
      permission: { kind: "denied", canAskAgain: false },
    });
    expect(location.permissionRequests).toBe(0);
    expect(location.measurements).toBe(0);

    const record = await store.get("forest-edge");
    if (record === null) throw new Error("fixture missing");
    await store.saveWithCommand({
      id: record.id,
      expectedLocalRevision: record.localRevision,
      payload: { ...payload(record), title: "위치 없이 저장" },
    });
    expect(await store.get(record.id)).toMatchObject({
      title: "위치 없이 저장",
      location: undefined,
    });
  });

  it("ignores a late foreground result after app lifecycle invalidation", async () => {
    const { coordinator, location, store } = await setup();
    const measurement = deferred<{
      kind: "measured";
      latitude: number;
      longitude: number;
      accuracyMeters: number;
      measuredAt: string;
    }>();
    location.measurementResult = measurement.promise;
    const before = await store.snapshot();
    const pending = coordinator.measureLocation();
    while (location.measurements === 0) await Promise.resolve();
    coordinator.invalidateLocationMeasurement();
    measurement.resolve({ kind: "measured", ...LOCATION });

    expect(await pending).toEqual({ kind: "interrupted" });
    expect(await store.snapshot()).toEqual(before);
  });

  it("atomically replaces an unattempted location command when user removes location", async () => {
    const { store } = await setup();
    const original = await store.get("forest-edge");
    if (original === null) throw new Error("fixture missing");
    const withLocation = await store.saveWithCommand({
      id: original.id,
      expectedLocalRevision: original.localRevision,
      payload: payload(original, LOCATION),
    });
    await store.saveWithCommand({
      id: original.id,
      expectedLocalRevision: withLocation.record.localRevision,
      payload: payload(withLocation.record, undefined),
    });

    const snapshot = await store.snapshot();
    expect(snapshot.records.find((record) => record.id === original.id)?.location).toBeUndefined();
    expect(snapshot.outbox).toHaveLength(1);
    expect(snapshot.outbox[0]?.localRevision).toBe(3);
    expect(snapshot.outbox[0]?.payload?.location).toBeUndefined();
  });
});
