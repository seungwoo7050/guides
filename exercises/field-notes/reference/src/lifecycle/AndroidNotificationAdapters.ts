import type {
  AndroidNotificationChannelPort,
  NotificationPermissionPort,
  PushTokenPort,
} from "../../../lifecycle-engine/src/ports.ts";
import type {
  NotificationPermissionState,
  PushTokenResult,
} from "../../../lifecycle-engine/src/types.ts";

export type ExpoNotificationPermissionResponse = {
  status: string;
  granted: boolean;
  canAskAgain: boolean;
};

export type ExpoAndroidNotificationChannelInput = {
  name: string;
  importance: number;
};

/**
 * SDK 57-compatible structural surface. The reference app supplies the real
 * expo-notifications namespace; Node tests supply a deterministic fake.
 */
export interface ExpoAndroidNotificationsApi {
  setNotificationChannelAsync(
    channelId: string,
    channel: ExpoAndroidNotificationChannelInput,
  ): Promise<unknown>;
  getPermissionsAsync(): Promise<ExpoNotificationPermissionResponse>;
  requestPermissionsAsync(): Promise<ExpoNotificationPermissionResponse>;
  getExpoPushTokenAsync(options: {
    projectId: string;
  }): Promise<{ data: string }>;
}

export function mapAndroidNotificationPermission(
  response: ExpoNotificationPermissionResponse,
  runtimePermissionRequired: boolean,
): NotificationPermissionState {
  if (response.status === "granted" && response.granted) {
    return runtimePermissionRequired ? { kind: "granted" } : { kind: "not-required" };
  }
  if (runtimePermissionRequired && response.status === "undetermined") {
    return { kind: "not-determined" };
  }
  if (response.status === "denied" || !response.granted) {
    return {
      kind: "denied",
      canAskAgain: runtimePermissionRequired && response.canAskAgain,
    };
  }
  return { kind: "restricted", reason: "inconsistent-permission-response" };
}

export class ExpoAndroidNotificationChannelAdapter
  implements AndroidNotificationChannelPort
{
  readonly #api: Pick<
    ExpoAndroidNotificationsApi,
    "setNotificationChannelAsync"
  >;
  readonly #channelId: string;
  readonly #channel: ExpoAndroidNotificationChannelInput;

  constructor(input: {
    api: Pick<ExpoAndroidNotificationsApi, "setNotificationChannelAsync">;
    channelId: string;
    channel: ExpoAndroidNotificationChannelInput;
  }) {
    if (input.channelId.length === 0 || input.channel.name.length === 0) {
      throw new RangeError("notification channel id and name must not be empty");
    }
    if (!Number.isFinite(input.channel.importance)) {
      throw new RangeError("notification channel importance must be finite");
    }
    this.#api = input.api;
    this.#channelId = input.channelId;
    this.#channel = { ...input.channel };
  }

  async ensureChannel(): Promise<
    | { kind: "ready" }
    | { kind: "failed"; reason: string }
  > {
    try {
      await this.#api.setNotificationChannelAsync(
        this.#channelId,
        this.#channel,
      );
      return { kind: "ready" };
    } catch {
      return { kind: "failed", reason: "channel-setup-failed" };
    }
  }
}

export class ExpoAndroidNotificationPermissionAdapter
  implements NotificationPermissionPort
{
  readonly #api: Pick<
    ExpoAndroidNotificationsApi,
    "getPermissionsAsync" | "requestPermissionsAsync"
  >;
  readonly #runtimePermissionRequired: boolean;

  constructor(input: {
    api: Pick<
      ExpoAndroidNotificationsApi,
      "getPermissionsAsync" | "requestPermissionsAsync"
    >;
    runtimePermissionRequired: boolean;
  }) {
    this.#api = input.api;
    this.#runtimePermissionRequired = input.runtimePermissionRequired;
  }

  async current(): Promise<NotificationPermissionState> {
    try {
      return mapAndroidNotificationPermission(
        await this.#api.getPermissionsAsync(),
        this.#runtimePermissionRequired,
      );
    } catch {
      return { kind: "restricted", reason: "permission-read-failed" };
    }
  }

  async request(): Promise<NotificationPermissionState> {
    if (!this.#runtimePermissionRequired) {
      return this.current();
    }
    try {
      return mapAndroidNotificationPermission(
        await this.#api.requestPermissionsAsync(),
        true,
      );
    } catch {
      return { kind: "restricted", reason: "permission-request-failed" };
    }
  }
}

export class ExpoPushTokenAdapter implements PushTokenPort {
  readonly #api: Pick<ExpoAndroidNotificationsApi, "getExpoPushTokenAsync">;
  readonly #projectId: string;

  constructor(input: {
    api: Pick<ExpoAndroidNotificationsApi, "getExpoPushTokenAsync">;
    projectId: string;
  }) {
    if (input.projectId.length === 0) {
      throw new RangeError("Expo project id must not be empty");
    }
    this.#api = input.api;
    this.#projectId = input.projectId;
  }

  async getToken(): Promise<PushTokenResult> {
    try {
      const result = await this.#api.getExpoPushTokenAsync({
        projectId: this.#projectId,
      });
      if (typeof result.data !== "string" || result.data.length === 0) {
        return { kind: "failed", reason: "invalid-token-response" };
      }
      return { kind: "token", token: result.data };
    } catch {
      return { kind: "failed", reason: "token-acquisition-failed" };
    }
  }
}
