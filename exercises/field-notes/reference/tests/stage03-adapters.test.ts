import type { PermissionState } from "@field-notes/shared";
import {
  ExpoImagePickerCameraAdapter,
  ExpoPendingImagePickerResultAdapter,
  ExpoSystemPhotoPickerAdapter,
  type ExpoImagePickerApi,
  normalizeImagePickerResult,
} from "../src/device/ExpoImagePickerAdapters";
import {
  ExpoForegroundLocationAdapter,
  normalizeForegroundLocation,
  type ExpoLocationApi,
} from "../src/device/ExpoForegroundLocationAdapter";
import {
  mapExpoLocationPermission,
  mapExpoPermission,
  nativeModuleAvailability,
} from "../src/device/permissionMapping";

const granted = {
  status: "granted",
  granted: true,
  canAskAgain: true,
  expires: "never",
} as const;

function imageApi(overrides: Record<string, unknown> = {}): ExpoImagePickerApi {
  return {
    getCameraPermissionsAsync: jest.fn(async () => granted),
    requestCameraPermissionsAsync: jest.fn(async () => granted),
    launchCameraAsync: jest.fn(async () => ({ canceled: true, assets: null })),
    launchImageLibraryAsync: jest.fn(async () => ({ canceled: true, assets: null })),
    getPendingResultAsync: jest.fn(async () => null),
    ...overrides,
  } as unknown as ExpoImagePickerApi;
}

function locationApi(overrides: Record<string, unknown> = {}): ExpoLocationApi {
  return {
    hasServicesEnabledAsync: jest.fn(async () => true),
    getForegroundPermissionsAsync: jest.fn(async () => granted),
    requestForegroundPermissionsAsync: jest.fn(async () => granted),
    getCurrentPositionAsync: jest.fn(async () => ({
      coords: {
        latitude: 37.5,
        longitude: 127,
        altitude: null,
        accuracy: 8,
        altitudeAccuracy: null,
        heading: null,
        speed: null,
      },
      timestamp: Date.parse("2026-08-09T15:00:00.000Z"),
    })),
    ...overrides,
  } as unknown as ExpoLocationApi;
}

describe("Stage 03 Expo adapter mapping", () => {
  it("keeps availability and permission independent and does not invent restricted", async () => {
    expect(nativeModuleAvailability("android", "camera")).toEqual({ kind: "available" });
    expect(nativeModuleAvailability("unsupported", "camera")).toEqual(
      expect.objectContaining({ kind: "unavailable" }),
    );
    expect(
      mapExpoPermission({ status: "denied", granted: false, canAskAgain: false }),
    ).toEqual({ kind: "denied", canAskAgain: false });
    expect(
      mapExpoPermission({ status: "undetermined", granted: false, canAskAgain: true }),
    ).toEqual({ kind: "not-determined" });
    expect(
      mapExpoLocationPermission({ ...granted, ios: { accuracy: "reduced" } }),
    ).toEqual(expect.objectContaining({ kind: "limited" }));
    expect(
      mapExpoLocationPermission({ ...granted, android: { accuracy: "coarse" } }),
    ).toEqual(expect.objectContaining({ kind: "limited" }));
  });

  it("uses the system picker without querying or requesting library-wide permission", async () => {
    const getLibraryPermission = jest.fn();
    const requestLibraryPermission = jest.fn();
    const api = imageApi({
      launchImageLibraryAsync: jest.fn(async () => ({
        canceled: false,
        assets: [
          {
            uri: "provider://selected-one",
            width: 100,
            height: 80,
            type: "image",
            mimeType: "image/jpeg",
          },
        ],
      })),
    }) as ExpoImagePickerApi & {
      getMediaLibraryPermissionsAsync?: typeof getLibraryPermission;
      requestMediaLibraryPermissionsAsync?: typeof requestLibraryPermission;
    };
    api.getMediaLibraryPermissionsAsync = getLibraryPermission;
    api.requestMediaLibraryPermissionsAsync = requestLibraryPermission;
    const picker = new ExpoSystemPhotoPickerAdapter(api, "android");

    expect(await picker.permission()).toEqual({ kind: "not-required" });
    expect(await picker.requestPermission()).toEqual({ kind: "not-required" });
    expect(await picker.choose()).toEqual({
      kind: "acquired",
      temporaryUri: "provider://selected-one",
      mimeType: "image/jpeg",
    });
    expect(getLibraryPermission).not.toHaveBeenCalled();
    expect(requestLibraryPermission).not.toHaveBeenCalled();
  });

  it("rechecks camera permission immediately before launch and preserves revoke", async () => {
    let permission: typeof granted | {
      status: "denied";
      granted: false;
      canAskAgain: false;
      expires: "never";
    } = granted;
    const launch = jest.fn(async () => ({ canceled: true, assets: null }) as const);
    const api = imageApi({
      getCameraPermissionsAsync: jest.fn(async () => permission),
      launchCameraAsync: launch,
    });
    const camera = new ExpoImagePickerCameraAdapter(api, "ios");
    expect(await camera.permission()).toEqual({ kind: "granted" });
    permission = {
      status: "denied",
      granted: false,
      canAskAgain: false,
      expires: "never",
    };

    expect(await camera.capture()).toEqual(
      expect.objectContaining({ kind: "failed", code: "permission-revoked" }),
    );
    expect(launch).not.toHaveBeenCalled();
  });

  it("reports real no-camera probes and keeps an unprobed mobile camera unknown", async () => {
    const unavailable = new ExpoImagePickerCameraAdapter(
      imageApi(),
      "android",
      async () => false,
    );
    expect(await unavailable.availability()).toEqual({
      kind: "unavailable",
      reason: "camera hardware is unavailable",
    });
    expect(await new ExpoImagePickerCameraAdapter(imageApi(), "ios").availability())
      .toEqual(expect.objectContaining({ kind: "limited" }));
    const never = new Promise<boolean | null>(() => undefined);
    await expect(new ExpoImagePickerCameraAdapter(
      imageApi(),
      "android",
      () => never,
      1,
    ).availability()).resolves.toEqual(expect.objectContaining({ kind: "limited" }));
    expect(() => new ExpoImagePickerCameraAdapter(
      imageApi(),
      "android",
      async () => null,
      0,
    )).toThrow("deadline must be positive");
  });

  it("maps a second camera permission-query rejection to a retryable result", async () => {
    let query = 0;
    const launch = jest.fn();
    const camera = new ExpoImagePickerCameraAdapter(imageApi({
      getCameraPermissionsAsync: jest.fn(async () => {
        query += 1;
        if (query === 2) throw new Error("native permission bridge unavailable");
        return granted;
      }),
      launchCameraAsync: launch,
    }), "android");

    expect(await camera.permission()).toEqual({ kind: "granted" });
    expect(await camera.capture()).toEqual(
      expect.objectContaining({ kind: "failed", code: "permission-revoked" }),
    );
    expect(launch).not.toHaveBeenCalled();
  });

  it("separates picker cancel, pending error, and invalid success", async () => {
    expect(normalizeImagePickerResult({ canceled: true, assets: null }, "launch")).toEqual({
      kind: "cancelled",
    });
    expect(
      normalizeImagePickerResult({ code: "E_ACTIVITY", message: "lost" }, "recovery"),
    ).toEqual(expect.objectContaining({ kind: "failed", code: "interrupted" }));
    expect(
      normalizeImagePickerResult({ canceled: false, assets: [] }, "launch"),
    ).toEqual(expect.objectContaining({ kind: "failed", code: "invalid-result" }));

    const iosPending = new ExpoPendingImagePickerResultAdapter(imageApi(), "ios");
    expect(await iosPending.recoverPending()).toBeNull();
  });

  it("queries location services separately and rejects null accuracy without fallback", async () => {
    const permissionQuery = jest.fn(async () => ({
      ...granted,
      android: { accuracy: "coarse" as const },
    }));
    const servicesQuery = jest.fn(async () => true);
    const api = locationApi({
      hasServicesEnabledAsync: servicesQuery,
      getForegroundPermissionsAsync: permissionQuery,
      getCurrentPositionAsync: jest.fn(async () => ({
        coords: {
          latitude: 37.5,
          longitude: 127,
          altitude: null,
          accuracy: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
        },
        timestamp: Date.parse("2026-08-09T15:00:00.000Z"),
      })),
    });
    const location = new ExpoForegroundLocationAdapter(api, "android", 100);

    expect(await location.availability()).toEqual({ kind: "available" });
    expect(permissionQuery).not.toHaveBeenCalled();
    expect(await location.permission()).toEqual(
      expect.objectContaining({ kind: "limited" }),
    );
    expect(await location.current()).toEqual(
      expect.objectContaining({ kind: "failed", reason: expect.stringContaining("invalid") }),
    );
    expect(servicesQuery).toHaveBeenCalled();
  });

  it("returns unavailable location without requesting permission", async () => {
    const permissionQuery = jest.fn(async () => granted);
    const location = new ExpoForegroundLocationAdapter(
      locationApi({
        hasServicesEnabledAsync: jest.fn(async () => false),
        getForegroundPermissionsAsync: permissionQuery,
      }),
      "android",
    );
    expect(await location.current()).toEqual(
      expect.objectContaining({ kind: "unavailable" }),
    );
    expect(permissionQuery).not.toHaveBeenCalled();
  });

  it("maps a second foreground-location permission-query rejection without throwing", async () => {
    let query = 0;
    const measure = jest.fn();
    const location = new ExpoForegroundLocationAdapter(locationApi({
      getForegroundPermissionsAsync: jest.fn(async () => {
        query += 1;
        if (query === 2) throw new Error("permission bridge unavailable");
        return granted;
      }),
      getCurrentPositionAsync: measure,
    }), "android", 100);

    expect(await location.permission()).toEqual({ kind: "granted" });
    await expect(location.current()).resolves.toEqual(
      expect.objectContaining({ kind: "failed", reason: expect.stringContaining("rechecked") }),
    );
    expect(measure).not.toHaveBeenCalled();
  });

  it("rejects finite timestamps outside the Date range without throwing", () => {
    const raw = {
      coords: {
        latitude: 37.5,
        longitude: 127,
        altitude: null,
        accuracy: 8,
        altitudeAccuracy: null,
        heading: null,
        speed: null,
      },
      timestamp: Number.MAX_VALUE,
    } as Awaited<ReturnType<ExpoLocationApi["getCurrentPositionAsync"]>>;

    expect(() => normalizeForegroundLocation(raw)).not.toThrow();
    expect(normalizeForegroundLocation(raw)).toEqual(
      expect.objectContaining({ kind: "failed", reason: expect.stringContaining("invalid") }),
    );
  });

  it("keeps the public not-required state distinct from limited", () => {
    const state: PermissionState = { kind: "not-required" };
    expect(state).not.toEqual({ kind: "limited", description: "selected item" });
  });
});
