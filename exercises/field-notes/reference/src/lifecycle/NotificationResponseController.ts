import {
  type NotificationNavigationIntent,
  NotificationIntentCoordinator,
  parseNotificationEnvelope,
} from "@field-notes/lifecycle-engine";
import type { DurableNotificationResponseHandler } from "./ExpoNotificationResponseSource";

export type NotificationResponseWithData = {
  notification?: {
    request?: {
      content?: { data?: unknown };
    };
  };
};

export interface NotificationTerminalLedgerPort {
  recordTerminalUnclaimed(input: {
    messageId: string;
    code: string;
    completedAt: number;
  }): Promise<boolean>;
}

/**
 * Applies navigation before durable acknowledgement. An active edit draft
 * releases the claim and leaves the native response available for user retry.
 */
export class NotificationResponseController<
  Response extends NotificationResponseWithData,
> implements DurableNotificationResponseHandler<Response> {
  readonly #coordinator: NotificationIntentCoordinator;
  readonly #ledger: NotificationTerminalLedgerPort;
  readonly #draftActive: () => boolean;
  readonly #navigate: (intent: NotificationNavigationIntent) => Promise<void>;
  readonly #afterNavigation: () => Promise<void>;
  readonly #onPending: (pending: boolean) => void;
  readonly #now: () => number;

  constructor(input: {
    coordinator: NotificationIntentCoordinator;
    ledger: NotificationTerminalLedgerPort;
    draftActive: () => boolean;
    navigate(intent: NotificationNavigationIntent): Promise<void>;
    afterNavigation?(): Promise<void>;
    onPending?(pending: boolean): void;
    now?: () => number;
  }) {
    this.#coordinator = input.coordinator;
    this.#ledger = input.ledger;
    this.#draftActive = input.draftActive;
    this.#navigate = input.navigate;
    this.#afterNavigation = input.afterNavigation ?? (async () => undefined);
    this.#onPending = input.onPending ?? (() => undefined);
    this.#now = input.now ?? Date.now;
  }

  async handle(response: Response): Promise<
    | { kind: "acknowledged" }
    | { kind: "terminal"; code: string }
    | { kind: "retryable"; code: string }
  > {
    const raw = response.notification?.request?.content?.data;
    const prepared = await this.#coordinator.prepare(raw);
    if (prepared.kind === "rejected") {
      if (prepared.reason === "in-progress" || prepared.reason === "account-unavailable") {
        return { kind: "retryable", code: prepared.reason };
      }
      if (prepared.claim !== undefined) {
        if (this.#draftActive()) {
          await this.#coordinator.defer(prepared.claim);
          this.#onPending(true);
          return { kind: "retryable", code: "draft-active" };
        }
        if (prepared.safeNavigation !== undefined) {
          try {
            await this.#navigate(prepared.safeNavigation);
          } catch {
            await this.#coordinator.defer(prepared.claim);
            return { kind: "retryable", code: "navigation-failed" };
          }
        }
        await this.#coordinator.reject(prepared.claim, prepared.reason);
      }
      const parsed = parseNotificationEnvelope(raw);
      if (prepared.claim === undefined && parsed.kind === "valid") {
        await this.#ledger.recordTerminalUnclaimed({
          messageId: parsed.envelope.messageId,
          code: prepared.reason,
          completedAt: this.#now(),
        });
      }
      if (
        prepared.claim === undefined &&
        prepared.safeNavigation !== undefined &&
        !this.#draftActive()
      ) {
        await this.#navigate(prepared.safeNavigation);
      }
      this.#onPending(false);
      return { kind: "terminal", code: prepared.reason };
    }

    if (this.#draftActive()) {
      await this.#coordinator.defer(prepared.claim);
      this.#onPending(true);
      return { kind: "retryable", code: "draft-active" };
    }
    try {
      await this.#navigate(prepared.navigation);
    } catch {
      await this.#coordinator.defer(prepared.claim);
      return { kind: "retryable", code: "navigation-failed" };
    }
    await this.#coordinator.acknowledge(prepared.claim);
    this.#onPending(false);
    try {
      await this.#afterNavigation();
    } catch {
      // Navigation and claim are already durable; sync gets another lifecycle chance.
    }
    return { kind: "acknowledged" };
  }
}
