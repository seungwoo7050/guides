import type {
  CameraPort,
  CapabilityAvailability,
  LocationMeasurementResult,
  LocationPort,
  MediaAcquisitionResult,
  PendingMediaResultPort,
  PermissionState,
  PhotoPickerPort,
} from "@field-notes/shared";

export class DeterministicCameraAdapter implements CameraPort {
  public availabilityQueries = 0;
  public permissionQueries = 0;
  public permissionRequests = 0;
  public captures = 0;

  public constructor(
    public availabilityState: CapabilityAvailability = { kind: "available" },
    public permissionState: PermissionState = { kind: "granted" },
    public requestedPermission: PermissionState = { kind: "granted" },
    public captureResult: MediaAcquisitionResult = { kind: "cancelled" },
  ) {}

  public async availability(): Promise<CapabilityAvailability> {
    this.availabilityQueries += 1;
    return this.availabilityState;
  }

  public async permission(): Promise<PermissionState> {
    this.permissionQueries += 1;
    return this.permissionState;
  }

  public async requestPermission(): Promise<PermissionState> {
    this.permissionRequests += 1;
    this.permissionState = this.requestedPermission;
    return this.requestedPermission;
  }

  public async capture(): Promise<MediaAcquisitionResult> {
    this.captures += 1;
    return this.captureResult;
  }
}

export class DeterministicPhotoPickerAdapter implements PhotoPickerPort {
  public availabilityQueries = 0;
  public permissionQueries = 0;
  public permissionRequests = 0;
  public selections = 0;

  public constructor(
    public availabilityState: CapabilityAvailability = { kind: "available" },
    public selectionResult: MediaAcquisitionResult = { kind: "cancelled" },
  ) {}

  public async availability(): Promise<CapabilityAvailability> {
    this.availabilityQueries += 1;
    return this.availabilityState;
  }

  public async permission(): Promise<PermissionState> {
    this.permissionQueries += 1;
    return { kind: "not-required" };
  }

  public async requestPermission(): Promise<PermissionState> {
    this.permissionRequests += 1;
    return { kind: "not-required" };
  }

  public async choose(): Promise<MediaAcquisitionResult> {
    this.selections += 1;
    return this.selectionResult;
  }
}

export class DeterministicLocationAdapter implements LocationPort {
  public availabilityQueries = 0;
  public permissionQueries = 0;
  public permissionRequests = 0;
  public measurements = 0;

  public constructor(
    public availabilityState: CapabilityAvailability = { kind: "available" },
    public permissionState: PermissionState = { kind: "granted" },
    public requestedPermission: PermissionState = { kind: "granted" },
    public measurementResult:
      | LocationMeasurementResult
      | Promise<LocationMeasurementResult> = {
      kind: "failed",
      reason: "no deterministic measurement configured",
    },
  ) {}

  public async availability(): Promise<CapabilityAvailability> {
    this.availabilityQueries += 1;
    return this.availabilityState;
  }

  public async permission(): Promise<PermissionState> {
    this.permissionQueries += 1;
    return this.permissionState;
  }

  public async requestPermission(): Promise<PermissionState> {
    this.permissionRequests += 1;
    this.permissionState = this.requestedPermission;
    return this.requestedPermission;
  }

  public async current(): Promise<LocationMeasurementResult> {
    this.measurements += 1;
    return this.measurementResult;
  }
}

export class DeterministicPendingMediaAdapter implements PendingMediaResultPort {
  public recoveries = 0;

  public constructor(
    public result: MediaAcquisitionResult | null = null,
  ) {}

  public async recoverPending(): Promise<MediaAcquisitionResult | null> {
    this.recoveries += 1;
    return this.result;
  }
}

export type Deferred<Value> = {
  promise: Promise<Value>;
  resolve(value: Value): void;
};

export function deferred<Value>(): Deferred<Value> {
  let resolve: ((value: Value) => void) | undefined;
  const promise = new Promise<Value>((complete) => {
    resolve = complete;
  });
  return {
    promise,
    resolve(value: Value) {
      if (resolve === undefined) throw new Error("deferred resolver is unavailable");
      resolve(value);
    },
  };
}
