import type { CapabilityAvailability, PermissionState } from "@field-notes/shared";

export type ExpoPermissionLike = {
  status: "granted" | "denied" | "undetermined";
  granted: boolean;
  canAskAgain: boolean;
};

export type ExpoLocationPermissionLike = ExpoPermissionLike & {
  ios?: { accuracy: "full" | "reduced" };
  android?: { accuracy: "fine" | "coarse" | "none" };
};

export function mapExpoPermission(raw: ExpoPermissionLike): PermissionState {
  if (raw.status === "undetermined") return { kind: "not-determined" };
  if (raw.status === "denied" || !raw.granted) {
    return { kind: "denied", canAskAgain: raw.canAskAgain };
  }
  return { kind: "granted" };
}

export function mapExpoLocationPermission(
  raw: ExpoLocationPermissionLike,
): PermissionState {
  const base = mapExpoPermission(raw);
  if (base.kind !== "granted") return base;
  if (raw.ios?.accuracy === "reduced") {
    return {
      kind: "limited",
      description: "iOS reduced-accuracy foreground location",
    };
  }
  if (raw.android?.accuracy === "coarse") {
    return {
      kind: "limited",
      description: "Android approximate foreground location",
    };
  }
  if (raw.android?.accuracy === "none") {
    return {
      kind: "limited",
      description: "Android reported granted without a usable accuracy scope",
    };
  }
  return base;
}

export function nativeModuleAvailability(
  platform: string,
  feature: "camera" | "photo-picker" | "foreground-location",
): CapabilityAvailability {
  if (platform === "android" || platform === "ios") return { kind: "available" };
  if (platform === "web") {
    return {
      kind: "limited",
      description: `${feature} depends on browser user activation and browser capability`,
    };
  }
  return { kind: "unavailable", reason: `${feature} is not supported on this platform` };
}

export function permissionAllowsUse(permission: PermissionState): boolean {
  return permission.kind === "granted" || permission.kind === "limited";
}
