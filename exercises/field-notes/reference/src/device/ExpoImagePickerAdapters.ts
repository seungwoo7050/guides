import type {
  CameraPort,
  MediaAcquisitionResult,
  PendingMediaResultPort,
  PermissionState,
  PhotoPickerPort,
} from "@field-notes/shared";
import * as ImagePicker from "expo-image-picker";
import { Platform } from "react-native";
import {
  mapExpoPermission,
  nativeModuleAvailability,
  permissionAllowsUse,
} from "./permissionMapping";

export type ExpoImagePickerApi = Pick<
  typeof ImagePicker,
  | "getCameraPermissionsAsync"
  | "requestCameraPermissionsAsync"
  | "launchCameraAsync"
  | "launchImageLibraryAsync"
  | "getPendingResultAsync"
>;

export type CameraAvailabilityProbe = () => Promise<boolean | null>;

const CAMERA_AVAILABILITY_DEADLINE_MS = 250;

async function boundedCameraAvailability(
  probe: CameraAvailabilityProbe,
  deadlineMs: number,
): Promise<boolean | null> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      probe(),
      new Promise<null>((resolve) => {
        timer = setTimeout(() => resolve(null), deadlineMs);
      }),
    ]);
  } catch {
    return null;
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

type PickerRawResult = Awaited<
  ReturnType<ExpoImagePickerApi["getPendingResultAsync"]>
>;

export function normalizeImagePickerResult(
  result: PickerRawResult,
  context: "launch" | "recovery",
): MediaAcquisitionResult | null {
  if (result === null) return null;
  if ("code" in result) {
    return {
      kind: "failed",
      code: context === "recovery" ? "interrupted" : "launch-failed",
      reason:
        context === "recovery"
          ? "platform returned a pending image-picker error"
          : "platform image UI failed",
    };
  }
  if (result.canceled) return { kind: "cancelled" };
  const asset = result.assets[0];
  if (
    result.assets.length !== 1 ||
    asset === undefined ||
    asset.uri.trim() === "" ||
    (asset.type !== undefined && asset.type !== "image")
  ) {
    return {
      kind: "failed",
      code: "invalid-result",
      reason: "image UI returned no single usable image",
    };
  }
  return {
    kind: "acquired",
    temporaryUri: asset.uri,
    mimeType: asset.mimeType,
  };
}

const IMAGE_OPTIONS = {
  mediaTypes: ["images"],
  allowsEditing: false,
  allowsMultipleSelection: false,
  selectionLimit: 1,
  quality: 1,
  exif: false,
  base64: false,
} as const satisfies ImagePicker.ImagePickerOptions;

export class ExpoImagePickerCameraAdapter implements CameraPort {
  public constructor(
    private readonly api: ExpoImagePickerApi = ImagePicker,
    private readonly platform: string = Platform.OS,
    private readonly availabilityProbe: CameraAvailabilityProbe = async () => null,
    private readonly availabilityDeadlineMs = CAMERA_AVAILABILITY_DEADLINE_MS,
  ) {}

  public async availability() {
    const module = nativeModuleAvailability(this.platform, "camera");
    if (module.kind === "unavailable" || this.platform === "web") return module;
    const available = await boundedCameraAvailability(
      this.availabilityProbe,
      this.availabilityDeadlineMs,
    );
    if (available === true) return { kind: "available" } as const;
    if (available === false) {
      return { kind: "unavailable", reason: "camera hardware is unavailable" } as const;
    }
    return {
      kind: "limited",
      description: "camera hardware availability is unknown until explicit launch",
    } as const;
  }

  public async permission() {
    return mapExpoPermission(await this.api.getCameraPermissionsAsync());
  }

  public async requestPermission() {
    return mapExpoPermission(await this.api.requestCameraPermissionsAsync());
  }

  public async capture(): Promise<MediaAcquisitionResult> {
    let current: PermissionState;
    try {
      current = await this.permission();
    } catch {
      return {
        kind: "failed",
        code: "permission-revoked",
        reason: "camera permission could not be rechecked at capture time",
      };
    }
    if (!permissionAllowsUse(current)) {
      return {
        kind: "failed",
        code: "permission-revoked",
        reason: "camera permission is not available at capture time",
      };
    }
    try {
      return (
        normalizeImagePickerResult(
          await this.api.launchCameraAsync(IMAGE_OPTIONS),
          "launch",
        ) ?? {
          kind: "failed",
          code: "invalid-result",
          reason: "camera returned no result",
        }
      );
    } catch {
      return {
        kind: "failed",
        code: "launch-failed",
        reason: "camera session failed or was interrupted",
      };
    }
  }
}

export class ExpoSystemPhotoPickerAdapter implements PhotoPickerPort {
  public constructor(
    private readonly api: ExpoImagePickerApi = ImagePicker,
    private readonly platform: string = Platform.OS,
  ) {}

  public async availability() {
    return nativeModuleAvailability(this.platform, "photo-picker");
  }

  public async permission() {
    return { kind: "not-required" } as const;
  }

  public async requestPermission() {
    return { kind: "not-required" } as const;
  }

  public async choose(): Promise<MediaAcquisitionResult> {
    try {
      return (
        normalizeImagePickerResult(
          await this.api.launchImageLibraryAsync(IMAGE_OPTIONS),
          "launch",
        ) ?? {
          kind: "failed",
          code: "invalid-result",
          reason: "system photo picker returned no result",
        }
      );
    } catch {
      return {
        kind: "failed",
        code: "launch-failed",
        reason: "system photo picker failed or was interrupted",
      };
    }
  }
}

export class ExpoPendingImagePickerResultAdapter
  implements PendingMediaResultPort
{
  public constructor(
    private readonly api: ExpoImagePickerApi = ImagePicker,
    private readonly platform: string = Platform.OS,
  ) {}

  public async recoverPending(): Promise<MediaAcquisitionResult | null> {
    if (this.platform !== "android") return null;
    try {
      return normalizeImagePickerResult(
        await this.api.getPendingResultAsync(),
        "recovery",
      );
    } catch {
      return {
        kind: "failed",
        code: "interrupted",
        reason: "Android pending image result could not be recovered",
      };
    }
  }
}
