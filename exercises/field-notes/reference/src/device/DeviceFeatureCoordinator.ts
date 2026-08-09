import type {
  Attachment,
  AttachmentFileStore,
  CameraPort,
  CapabilityAvailability,
  Clock,
  ExternalMediaOperation,
  ExternalMediaOperationRepository,
  IdGenerator,
  LocationPort,
  MediaAcquisitionResult,
  MediaSource,
  PendingMediaResultPort,
  PermissionState,
  PhotoPickerPort,
  RecordPayload,
} from "@field-notes/shared";
import { permissionAllowsUse } from "./permissionMapping";

const OPERATION_LIFETIME_MS = 15 * 60 * 1000;
const MAX_IMAGE_BYTES = 20 * 1024 * 1024;
const SUPPORTED_IMAGE_MIME_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/heic",
  "image/heif",
  "image/webp",
]);

export type CapabilityAccess = {
  availability: CapabilityAvailability;
  permission: PermissionState;
};

export type DeviceCapabilitySnapshot = {
  camera: CapabilityAccess;
  photoPicker: CapabilityAccess;
  location: CapabilityAccess;
};

export type MediaActionOutcome =
  | { kind: "attached"; attachment: Attachment; recovered: boolean }
  | { kind: "cancelled" }
  | { kind: "denied"; permission: PermissionState }
  | { kind: "unavailable"; reason: string }
  | { kind: "failed"; code: string; reason: string }
  | { kind: "interrupted"; reason: string }
  | { kind: "duplicate" }
  | { kind: "busy" }
  | { kind: "none" };

export type LocationActionOutcome =
  | { kind: "preview"; location: NonNullable<RecordPayload["location"]> }
  | { kind: "denied"; permission: PermissionState }
  | { kind: "unavailable"; reason: string }
  | { kind: "failed"; reason: string }
  | { kind: "interrupted" };

type MediaPort = Pick<
  CameraPort | PhotoPickerPort,
  "availability" | "permission" | "requestPermission"
>;

export class DeviceFeatureCoordinator {
  private launchInFlightOperationId: string | null = null;
  private locationGeneration = 0;

  public constructor(
    private readonly camera: CameraPort,
    private readonly photoPicker: PhotoPickerPort,
    private readonly location: LocationPort,
    private readonly pendingMedia: PendingMediaResultPort,
    private readonly operations: ExternalMediaOperationRepository,
    private readonly files: AttachmentFileStore,
    private readonly clock: Clock,
    private readonly ids: IdGenerator,
  ) {}

  private async safeAccess(port: MediaPort | LocationPort): Promise<CapabilityAccess> {
    let availability: CapabilityAvailability;
    try {
      availability = await port.availability();
    } catch {
      availability = { kind: "unavailable", reason: "capability query failed" };
    }
    let permission: PermissionState;
    try {
      permission = await port.permission();
    } catch {
      permission = {
        kind: "restricted",
        reason: "permission state could not be read",
      };
    }
    return { availability, permission };
  }

  public async inspectCapabilities(): Promise<DeviceCapabilitySnapshot> {
    const [camera, photoPicker, location] = await Promise.all([
      this.safeAccess(this.camera),
      this.safeAccess(this.photoPicker),
      this.safeAccess(this.location),
    ]);
    return { camera, photoPicker, location };
  }

  private async permissionForExplicitAction(
    port: MediaPort | LocationPort,
    current: PermissionState,
  ): Promise<PermissionState> {
    if (permissionAllowsUse(current) || current.kind === "not-required") {
      return current;
    }
    if (
      current.kind === "not-determined" ||
      (current.kind === "denied" && current.canAskAgain)
    ) {
      return port.requestPermission();
    }
    return current;
  }

  private denied(permission: PermissionState): MediaActionOutcome {
    return { kind: "denied", permission };
  }

  public capturePhoto(recordId: string): Promise<MediaActionOutcome> {
    return this.launchMedia(recordId, "camera", this.camera, () =>
      this.camera.capture(),
    );
  }

  public pickPhoto(recordId: string): Promise<MediaActionOutcome> {
    return this.launchMedia(recordId, "photo-picker", this.photoPicker, () =>
      this.photoPicker.choose(),
    );
  }

  private async launchMedia(
    recordId: string,
    source: MediaSource,
    port: MediaPort,
    launch: () => Promise<MediaAcquisitionResult>,
  ): Promise<MediaActionOutcome> {
    if (this.launchInFlightOperationId !== null) return { kind: "busy" };
    const availability = await port.availability().catch(
      (): CapabilityAvailability => ({
        kind: "unavailable",
        reason: `${source} availability query failed`,
      }),
    );
    if (availability.kind === "unavailable") {
      return { kind: "unavailable", reason: availability.reason };
    }
    let permission: PermissionState;
    try {
      permission = await this.permissionForExplicitAction(
        port,
        await port.permission(),
      );
    } catch {
      return {
        kind: "failed",
        code: "permission-query-failed",
        reason: `${source} permission could not be resolved`,
      };
    }
    if (!(permissionAllowsUse(permission) || permission.kind === "not-required")) {
      return this.denied(permission);
    }

    const createdAt = this.clock.now();
    const operationId = this.ids.externalOperationId();
    const expiresAt = new Date(
      Date.parse(createdAt) + OPERATION_LIFETIME_MS,
    ).toISOString();
    let operation: ExternalMediaOperation;
    try {
      operation = await this.operations.beginExternalMediaOperation({
        operationId,
        recordId,
        source,
        createdAt,
        expiresAt,
      });
    } catch {
      return { kind: "busy" };
    }

    this.launchInFlightOperationId = operation.operationId;
    try {
      return await this.consumeMediaResult(operation, await launch(), false);
    } finally {
      this.launchInFlightOperationId = null;
    }
  }

  private async terminate(
    operation: ExternalMediaOperation,
    state: "cancelled" | "failed" | "interrupted",
    reason?: string,
  ): Promise<boolean> {
    return this.operations.finishExternalMediaOperation({
      operationId: operation.operationId,
      state,
      completedAt: this.clock.now(),
      failureReason: reason,
    });
  }

  private normalizedMimeType(result: MediaAcquisitionResult & { kind: "acquired" }):
    | { kind: "accepted"; mimeType: string }
    | { kind: "rejected" } {
    if (result.mimeType === undefined || result.mimeType.trim() === "") {
      return { kind: "accepted", mimeType: "application/octet-stream" };
    }
    const mimeType = result.mimeType.toLowerCase();
    return SUPPORTED_IMAGE_MIME_TYPES.has(mimeType)
      ? { kind: "accepted", mimeType }
      : { kind: "rejected" };
  }

  private async consumeMediaResult(
    operation: ExternalMediaOperation,
    result: MediaAcquisitionResult,
    recovered: boolean,
  ): Promise<MediaActionOutcome> {
    if (result.kind === "cancelled") {
      const completed = await this.terminate(operation, "cancelled");
      return completed ? { kind: "cancelled" } : { kind: "duplicate" };
    }
    if (result.kind === "failed") {
      const state = result.code === "interrupted" ? "interrupted" : "failed";
      const completed = await this.terminate(operation, state, result.code);
      if (!completed) return { kind: "duplicate" };
      return state === "interrupted"
        ? { kind: "interrupted", reason: result.reason }
        : { kind: "failed", code: result.code, reason: result.reason };
    }

    const mime = this.normalizedMimeType(result);
    if (mime.kind === "rejected") {
      await this.terminate(operation, "failed", "unsupported-media-type");
      return {
        kind: "failed",
        code: "unsupported-media-type",
        reason: "selected result is not a supported image type",
      };
    }
    if (!(await this.operations.claimExternalMediaResult(operation.operationId))) {
      return { kind: "duplicate" };
    }

    let owned: Awaited<ReturnType<AttachmentFileStore["takeOwnership"]>>;
    try {
      owned = await this.files.takeOwnership(result.temporaryUri);
    } catch {
      await this.files.cleanupStaging().catch(() => undefined);
      await this.terminate(operation, "failed", "copy-failed");
      return {
        kind: "failed",
        code: "copy-failed",
        reason: "selected image could not be copied into app-owned storage",
      };
    }
    if (owned.byteSize > MAX_IMAGE_BYTES) {
      await this.files.remove(owned.ownedUri).catch(() => undefined);
      await this.terminate(operation, "failed", "file-too-large");
      return {
        kind: "failed",
        code: "file-too-large",
        reason: "selected image exceeds the 20 MiB local safety limit",
      };
    }

    try {
      const completion = await this.operations.completeExternalMediaWithAttachment({
        operationId: operation.operationId,
        completedAt: this.clock.now(),
        attachment: {
          id: this.ids.attachmentId(),
          recordId: operation.recordId,
          localUri: owned.ownedUri,
          checksum: owned.checksum,
          byteSize: owned.byteSize,
          mimeType: mime.mimeType,
        },
      });
      if (completion.kind === "stale") {
        await this.files.remove(owned.ownedUri).catch(() => undefined);
        return { kind: "duplicate" };
      }
      return { kind: "attached", attachment: completion.attachment, recovered };
    } catch {
      await this.terminate(operation, "failed", "metadata-commit-failed").catch(
        () => undefined,
      );
      return {
        kind: "failed",
        code: "metadata-commit-failed",
        reason: "owned image metadata could not be committed",
      };
    }
  }

  public async recoverPendingMedia(): Promise<MediaActionOutcome> {
    if (this.launchInFlightOperationId !== null) return { kind: "busy" };
    const operation = await this.operations.activeExternalMediaOperation();
    if (operation === null) {
      const stale = await this.pendingMedia.recoverPending();
      return stale === null ? { kind: "none" } : { kind: "duplicate" };
    }
    if (
      operation.state === "copying" ||
      Date.parse(operation.expiresAt) <= Date.parse(this.clock.now())
    ) {
      await this.terminate(operation, "interrupted", "expired-or-partial-operation");
      return {
        kind: "interrupted",
        reason: "external media operation was interrupted; choose or capture again",
      };
    }
    const result = await this.pendingMedia.recoverPending();
    if (result === null) {
      await this.terminate(operation, "interrupted", "pending-result-unavailable");
      return {
        kind: "interrupted",
        reason: "platform supplied no recoverable result; choose or capture again",
      };
    }
    return this.consumeMediaResult(operation, result, true);
  }

  public invalidateLocationMeasurement(): void {
    this.locationGeneration += 1;
  }

  public async measureLocation(): Promise<LocationActionOutcome> {
    const availability = await this.location.availability().catch(
      (): CapabilityAvailability => ({
        kind: "unavailable",
        reason: "location availability query failed",
      }),
    );
    if (availability.kind === "unavailable") {
      return { kind: "unavailable", reason: availability.reason };
    }
    let permission: PermissionState;
    try {
      permission = await this.permissionForExplicitAction(
        this.location,
        await this.location.permission(),
      );
    } catch {
      return { kind: "failed", reason: "location permission could not be resolved" };
    }
    if (!permissionAllowsUse(permission)) {
      return { kind: "denied", permission };
    }

    const generation = ++this.locationGeneration;
    const result = await this.location.current();
    if (generation !== this.locationGeneration) return { kind: "interrupted" };
    if (result.kind === "measured") {
      return {
        kind: "preview",
        location: {
          latitude: result.latitude,
          longitude: result.longitude,
          accuracyMeters: result.accuracyMeters,
          measuredAt: result.measuredAt,
        },
      };
    }
    if (result.kind === "permission-revoked") {
      return { kind: "denied", permission: result.permission };
    }
    return result.kind === "unavailable"
      ? { kind: "unavailable", reason: result.reason }
      : { kind: "failed", reason: result.reason };
  }
}
