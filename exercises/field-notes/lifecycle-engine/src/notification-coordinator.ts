import type {
  LifecycleClock,
  NotificationOwnerIdGenerator,
  NotificationStateRepository,
  ProcessedIntentClaimPort,
} from "./ports.ts";
import type {
  NotificationEnvelope,
  NotificationNavigationIntent,
  NotificationPrepareResult,
  ProcessedIntentClaim,
} from "./types.ts";
import { parseNotificationEnvelope } from "./notification-parser.ts";

export class NotificationIntentCoordinator {
  readonly #repository: NotificationStateRepository;
  readonly #claims: ProcessedIntentClaimPort;
  readonly #clock: LifecycleClock;
  readonly #owners: NotificationOwnerIdGenerator;
  readonly #claimLeaseMs: number;

  constructor(input: {
    repository: NotificationStateRepository;
    claims: ProcessedIntentClaimPort;
    clock: LifecycleClock;
    owners: NotificationOwnerIdGenerator;
    claimLeaseMs: number;
  }) {
    if (!Number.isFinite(input.claimLeaseMs) || input.claimLeaseMs <= 0) {
      throw new Error("claimLeaseMs must be positive");
    }
    this.#repository = input.repository;
    this.#claims = input.claims;
    this.#clock = input.clock;
    this.#owners = input.owners;
    this.#claimLeaseMs = input.claimLeaseMs;
  }

  async prepare(raw: unknown): Promise<NotificationPrepareResult> {
    const parsed = parseNotificationEnvelope(raw);
    if (parsed.kind === "invalid") {
      return {
        kind: "rejected",
        reason: "malformed",
        parseReason: parsed.reason,
      };
    }

    await this.#repository.ready();
    const account = await this.#repository.currentAccount();
    if (account.kind === "none") {
      return { kind: "rejected", reason: "account-unavailable" };
    }
    if (account.kind === "deleted") {
      return { kind: "rejected", reason: "account-deleted" };
    }
    if (account.accountId !== parsed.envelope.accountId) {
      return { kind: "rejected", reason: "account-mismatch" };
    }

    const claimed = await this.#claims.claim({
      messageId: parsed.envelope.messageId,
      ownerId: this.#owners.next(parsed.envelope.messageId),
      now: this.#clock.now(),
      leaseDurationMs: this.#claimLeaseMs,
    });
    if (claimed.kind === "duplicate") {
      return { kind: "rejected", reason: "duplicate" };
    }
    if (claimed.kind === "busy") {
      return { kind: "rejected", reason: "in-progress" };
    }

    try {
      return await this.#resolveClaimed(parsed.envelope, claimed.claim);
    } catch (error: unknown) {
      await this.#claims.release(claimed.claim);
      throw error;
    }
  }

  async acknowledge(claim: ProcessedIntentClaim): Promise<void> {
    await this.#claims.complete(claim);
  }

  async #rejectClaimed(
    claim: ProcessedIntentClaim,
    result: Extract<NotificationPrepareResult, { kind: "rejected" }>,
  ): Promise<NotificationPrepareResult> {
    await this.#claims.complete(claim);
    return result;
  }

  async #resolveClaimed(
    envelope: NotificationEnvelope,
    claim: ProcessedIntentClaim,
  ): Promise<NotificationPrepareResult> {
    const intent = envelope.intent;
    if (intent.kind === "sync-blocked") {
      if (!(await this.#repository.isSyncBlocked())) {
        return this.#rejectClaimed(claim, {
          kind: "rejected",
          reason: "stale",
          safeNavigation: { kind: "open-records" },
        });
      }
      return {
        kind: "prepared",
        envelope,
        claim,
        navigation: { kind: "open-sync", focus: "blocked" },
      };
    }

    const record = await this.#repository.recordState(intent.recordId);
    if (record === "deleted") {
      return this.#rejectClaimed(claim, {
        kind: "rejected",
        reason: "record-deleted",
        safeNavigation: { kind: "open-records" },
      });
    }
    if (record === "missing") {
      return this.#rejectClaimed(claim, {
        kind: "rejected",
        reason: "record-missing",
        safeNavigation: { kind: "open-records" },
      });
    }

    if (intent.kind === "record-updated") {
      return {
        kind: "prepared",
        envelope,
        claim,
        navigation: { kind: "open-record", recordId: intent.recordId },
      };
    }

    const conflict = await this.#repository.conflictState(intent.recordId);
    if (conflict !== "active") {
      const safeNavigation: NotificationNavigationIntent = {
        kind: "open-record",
        recordId: intent.recordId,
      };
      return this.#rejectClaimed(claim, {
        kind: "rejected",
        reason: "stale",
        safeNavigation,
      });
    }
    return {
      kind: "prepared",
      envelope,
      claim,
      navigation: {
        kind: "open-sync",
        focus: "conflict",
        recordId: intent.recordId,
      },
    };
  }
}
