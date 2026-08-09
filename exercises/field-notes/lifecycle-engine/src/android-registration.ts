import type {
  AndroidNotificationChannelPort,
  NotificationPermissionPort,
  PushTokenPort,
} from "./ports.ts";
import type {
  AndroidNotificationRegistrationResult,
  NotificationPermissionState,
} from "./types.ts";

export class AndroidNotificationRegistrationCoordinator {
  readonly #channels: AndroidNotificationChannelPort;
  readonly #permissions: NotificationPermissionPort;
  readonly #tokens: PushTokenPort;

  constructor(input: {
    channels: AndroidNotificationChannelPort;
    permissions: NotificationPermissionPort;
    tokens: PushTokenPort;
  }) {
    this.#channels = input.channels;
    this.#permissions = input.permissions;
    this.#tokens = input.tokens;
  }

  async register(input: {
    requestPermission: boolean;
  }): Promise<AndroidNotificationRegistrationResult> {
    const channel = await this.#channels.ensureChannel();
    if (channel.kind === "failed") {
      return { kind: "channel-failed", reason: channel.reason };
    }

    let permission = await this.#permissions.current();
    if (permission.kind === "not-determined") {
      if (!input.requestPermission) {
        return { kind: "permission-required" };
      }
      permission = await this.#permissions.request();
    }

    return this.#finish(permission);
  }

  async #finish(
    permission: NotificationPermissionState,
  ): Promise<AndroidNotificationRegistrationResult> {
    if (permission.kind === "not-determined") {
      return { kind: "permission-required" };
    }
    if (permission.kind === "denied") {
      return {
        kind: "permission-denied",
        canAskAgain: permission.canAskAgain,
      };
    }
    if (permission.kind === "restricted") {
      return { kind: "permission-restricted", reason: permission.reason };
    }

    const normalizedPermission = permission.kind;
    const token = await this.#tokens.getToken();
    if (token.kind === "failed") {
      return {
        kind: "token-failed",
        permission: normalizedPermission,
        reason: token.reason,
      };
    }
    return {
      kind: "token-ready",
      permission: normalizedPermission,
      token: token.token,
    };
  }
}
