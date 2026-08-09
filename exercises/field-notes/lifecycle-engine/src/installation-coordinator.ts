import type {
  LifecycleClock,
  NotificationInstallationRegistryPort,
} from "./ports.ts";
import type {
  NotificationInstallationLogoutResult,
  NotificationInstallationRegistrationResult,
  PushTokenResult,
} from "./types.ts";

function requireOpaqueId(value: string, label: string): void {
  if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) {
    throw new RangeError(`${label} must be a non-empty opaque identifier`);
  }
}

export class NotificationInstallationCoordinator {
  readonly #registry: NotificationInstallationRegistryPort;
  readonly #clock: LifecycleClock;

  constructor(input: {
    registry: NotificationInstallationRegistryPort;
    clock: LifecycleClock;
  }) {
    this.#registry = input.registry;
    this.#clock = input.clock;
  }

  async register(input: {
    installationId: string;
    accountId: string;
    token: PushTokenResult;
  }): Promise<NotificationInstallationRegistrationResult> {
    requireOpaqueId(input.installationId, "installationId");
    requireOpaqueId(input.accountId, "accountId");
    if (input.token.kind === "failed") {
      return {
        kind: "token-unavailable",
        installationId: input.installationId,
        accountId: input.accountId,
        reason: input.token.reason,
      };
    }
    if (input.token.token.length === 0) {
      throw new RangeError("push token must not be empty");
    }

    const updatedAt = this.#clock.now();
    if (!Number.isFinite(updatedAt)) {
      throw new RangeError("clock must return a finite timestamp");
    }
    const stored = await this.#registry.upsert({
      installationId: input.installationId,
      accountId: input.accountId,
      token: input.token.token,
      updatedAt,
    });
    if (stored.kind === "failed") {
      return {
        kind: "registry-failed",
        operation: "upsert",
        installationId: input.installationId,
        accountId: input.accountId,
        reason: stored.reason,
      };
    }

    const previous = stored.previous;
    const change =
      previous === null
        ? ({ kind: "created" } as const)
        : previous.accountId !== input.accountId
          ? ({
              kind: "account-switched",
              previousAccountId: previous.accountId,
            } as const)
          : previous.token === input.token.token
            ? ({ kind: "unchanged" } as const)
            : ({ kind: "rotated" } as const);
    return {
      kind: "registered",
      installationId: input.installationId,
      accountId: input.accountId,
      updatedAt,
      change,
    };
  }

  async logout(input: {
    installationId: string;
    accountId: string;
  }): Promise<NotificationInstallationLogoutResult> {
    requireOpaqueId(input.installationId, "installationId");
    requireOpaqueId(input.accountId, "accountId");
    const removed = await this.#registry.remove(input);
    if (removed.kind === "failed") {
      return {
        kind: "registry-failed",
        operation: "remove",
        installationId: input.installationId,
        accountId: input.accountId,
        reason: removed.reason,
      };
    }
    if (removed.kind === "account-mismatch") {
      return {
        kind: "account-mismatch",
        installationId: input.installationId,
        accountId: input.accountId,
        boundAccountId: removed.boundAccountId,
      };
    }
    if (removed.kind === "absent") {
      return {
        kind: "already-logged-out",
        installationId: input.installationId,
        accountId: input.accountId,
      };
    }
    return {
      kind: "logged-out",
      installationId: input.installationId,
      accountId: input.accountId,
    };
  }
}
