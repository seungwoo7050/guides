import type {
  CapabilityAvailability,
  LocationMeasurementResult,
  LocationPort,
  PermissionState,
} from "@field-notes/shared";
import * as Location from "expo-location";
import { Platform } from "react-native";
import {
  mapExpoLocationPermission,
  nativeModuleAvailability,
  permissionAllowsUse,
} from "./permissionMapping";

export type ExpoLocationApi = Pick<
  typeof Location,
  | "hasServicesEnabledAsync"
  | "getForegroundPermissionsAsync"
  | "requestForegroundPermissionsAsync"
  | "getCurrentPositionAsync"
>;

export type RawLocationObject = Awaited<
  ReturnType<ExpoLocationApi["getCurrentPositionAsync"]>
>;

export function normalizeForegroundLocation(
  raw: RawLocationObject,
): LocationMeasurementResult {
  const { latitude, longitude, accuracy } = raw.coords;
  const measuredAt = new Date(raw.timestamp);
  if (
    !Number.isFinite(latitude) ||
    latitude < -90 ||
    latitude > 90 ||
    !Number.isFinite(longitude) ||
    longitude < -180 ||
    longitude > 180 ||
    accuracy === null ||
    !Number.isFinite(accuracy) ||
    accuracy < 0 ||
    !Number.isFinite(raw.timestamp) ||
    !Number.isFinite(measuredAt.getTime())
  ) {
    return { kind: "failed", reason: "location provider returned invalid values" };
  }
  return {
    kind: "measured",
    latitude,
    longitude,
    accuracyMeters: accuracy,
    measuredAt: measuredAt.toISOString(),
  };
}

export class ExpoForegroundLocationAdapter implements LocationPort {
  public constructor(
    private readonly api: ExpoLocationApi = Location,
    private readonly platform: string = Platform.OS,
    private readonly deadlineMs = 15_000,
  ) {}

  public async availability(): Promise<CapabilityAvailability> {
    const module = nativeModuleAvailability(this.platform, "foreground-location");
    if (module.kind === "unavailable") return module;
    try {
      return (await this.api.hasServicesEnabledAsync())
        ? module
        : { kind: "unavailable", reason: "device location services are disabled" };
    } catch {
      return {
        kind: "unavailable",
        reason: "location services status could not be read",
      };
    }
  }

  public async permission(): Promise<PermissionState> {
    return mapExpoLocationPermission(
      await this.api.getForegroundPermissionsAsync(),
    );
  }

  public async requestPermission(): Promise<PermissionState> {
    return mapExpoLocationPermission(
      await this.api.requestForegroundPermissionsAsync(),
    );
  }

  public async current(): Promise<LocationMeasurementResult> {
    const availability = await this.availability();
    if (availability.kind === "unavailable") {
      return { kind: "unavailable", reason: availability.reason };
    }
    let currentPermission: PermissionState;
    try {
      currentPermission = await this.permission();
    } catch {
      return {
        kind: "failed",
        reason: "foreground location permission could not be rechecked",
      };
    }
    if (!permissionAllowsUse(currentPermission)) {
      return { kind: "permission-revoked", permission: currentPermission };
    }
    return new Promise<LocationMeasurementResult>((resolve) => {
      let settled = false;
      const finish = (result: LocationMeasurementResult) => {
        if (settled) return;
        settled = true;
        clearTimeout(deadline);
        resolve(result);
      };
      const deadline = setTimeout(
        () => finish({ kind: "failed", reason: "foreground location timed out" }),
        this.deadlineMs,
      );
      void this.api
        .getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
          mayShowUserSettingsDialog: false,
        })
        .then((value) => finish(normalizeForegroundLocation(value)))
        .catch(() =>
          finish({ kind: "failed", reason: "foreground location measurement failed" }),
        );
    });
  }
}
