import type {
  AccountReadinessState,
  ConflictReadinessState,
  NotificationStateRepository,
  ProcessedIntentClaim,
  ProcessedIntentClaimPort,
  ProcessedIntentClaimResult,
  ProcessedIntentCompletion,
  RecordReadinessState,
} from "@field-notes/lifecycle-engine";
import type { SQLiteDatabase } from "expo-sqlite";
import type { SQLiteFieldNotesRepository } from "../storage/SQLiteFieldNotesRepository";

export const LOCAL_DEMO_ACCOUNT_ID = "local-demo-account";

export type NotificationLedgerEntry = {
  messageId: string;
  state: "claimed" | "completed" | "terminal";
  leaseExpiresAt?: number;
  completedAt?: number;
  terminalCode?: string;
};

type NotificationIntentRow = {
  message_id: string;
  state: string;
  claim_token: string | null;
  claim_owner: string | null;
  lease_expires_at: number | null;
  completed_at: number | null;
  terminal_code: string | null;
};

const OPAQUE_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const OUTCOME_CODE = /^[a-z0-9][a-z0-9._:-]{0,63}$/;
let claimSequence = 0;

function defaultClaimToken(): string {
  claimSequence += 1;
  return `notification-claim-${Date.now().toString(36)}-${claimSequence.toString(36)}`;
}

function assertOpaqueId(value: string, field: string): void {
  if (!OPAQUE_ID.test(value)) throw new TypeError(`${field} is not a bounded opaque id`);
}

function assertFiniteTime(value: number, field: string): void {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new RangeError(`${field} must be a non-negative safe integer`);
  }
}

/**
 * Durable notification state and claim adapter over the same app-owned SQLite
 * database as records/outbox. It persists identities and safe outcome codes,
 * never notification content or push tokens.
 */
export class SQLiteNotificationRepository
  implements NotificationStateRepository, ProcessedIntentClaimPort
{
  readonly #repository: SQLiteFieldNotesRepository;
  readonly #account: () => Promise<AccountReadinessState>;
  readonly #claimToken: () => string;
  readonly #completionNow: () => number;

  constructor(input: {
    repository: SQLiteFieldNotesRepository;
    account?: () => Promise<AccountReadinessState>;
    claimToken?: () => string;
    completionNow?: () => number;
  }) {
    this.#repository = input.repository;
    this.#account = input.account ?? (async () => ({
      kind: "active",
      accountId: LOCAL_DEMO_ACCOUNT_ID,
    }));
    this.#claimToken = input.claimToken ?? defaultClaimToken;
    this.#completionNow = input.completionNow ?? Date.now;
  }

  async ready(): Promise<void> {
    await this.#repository.ready();
  }

  async currentAccount(): Promise<AccountReadinessState> {
    await this.ready();
    return this.#account();
  }

  async recordState(recordId: string): Promise<RecordReadinessState> {
    assertOpaqueId(recordId, "recordId");
    const db = await this.#db();
    const row = await db.getFirstAsync<{ deleted_at_local: string | null }>(
      "SELECT deleted_at_local FROM records WHERE id = ?",
      [recordId],
    );
    if (row === null) return "missing";
    return row.deleted_at_local === null ? "active" : "deleted";
  }

  async conflictState(recordId: string): Promise<ConflictReadinessState> {
    assertOpaqueId(recordId, "recordId");
    const db = await this.#db();
    const row = await db.getFirstAsync<{ resolution_kind: string | null }>(
      `SELECT resolution_kind FROM conflicts
       WHERE record_id = ? ORDER BY created_at DESC, conflict_id DESC LIMIT 1`,
      [recordId],
    );
    if (row === null) return "missing";
    return row.resolution_kind === null ? "active" : "resolved";
  }

  async isSyncBlocked(): Promise<boolean> {
    const db = await this.#db();
    const row = await db.getFirstAsync<{ present: number }>(
      "SELECT 1 AS present FROM outbox WHERE state = 'blocked-auth' LIMIT 1",
    );
    return row !== null;
  }

  async claim(input: {
    messageId: string;
    ownerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ProcessedIntentClaimResult> {
    assertOpaqueId(input.messageId, "messageId");
    assertOpaqueId(input.ownerId, "ownerId");
    assertFiniteTime(input.now, "now");
    if (!Number.isSafeInteger(input.leaseDurationMs) || input.leaseDurationMs <= 0) {
      throw new RangeError("leaseDurationMs must be a positive safe integer");
    }
    const expiresAt = input.now + input.leaseDurationMs;
    assertFiniteTime(expiresAt, "expiresAt");
    const db = await this.#db();
    let result: ProcessedIntentClaimResult | undefined;
    await db.withExclusiveTransactionAsync(async (txn) => {
      const current = await txn.getFirstAsync<NotificationIntentRow>(
        "SELECT * FROM processed_intents WHERE message_id = ?",
        [input.messageId],
      );
      if (current?.state === "completed" || current?.state === "terminal") {
        result = { kind: "duplicate" };
        return;
      }
      if (
        current?.state === "claimed" &&
        current.lease_expires_at !== null &&
        current.lease_expires_at > input.now
      ) {
        result = { kind: "busy" };
        return;
      }
      const token = this.#claimToken();
      assertOpaqueId(token, "claimToken");
      if (current === null) {
        await txn.runAsync(
          `INSERT INTO processed_intents (
             message_id, state, claim_token, claim_owner, lease_expires_at
           ) VALUES (?, 'claimed', ?, ?, ?)`,
          [input.messageId, token, input.ownerId, expiresAt],
        );
      } else {
        const update = await txn.runAsync(
          `UPDATE processed_intents
           SET state = 'claimed', claim_token = ?, claim_owner = ?,
               lease_expires_at = ?, completed_at = NULL, terminal_code = NULL
           WHERE message_id = ? AND state = 'claimed'
             AND lease_expires_at <= ?`,
          [token, input.ownerId, expiresAt, input.messageId, input.now],
        );
        if (update.changes !== 1) {
          result = { kind: "busy" };
          return;
        }
      }
      result = {
        kind: "claimed",
        claim: {
          messageId: input.messageId,
          token,
          ownerId: input.ownerId,
          expiresAt,
        },
      };
    });
    if (result === undefined) throw new Error("notification claim transaction produced no result");
    return result;
  }

  async complete(
    claim: ProcessedIntentClaim,
    outcome: ProcessedIntentCompletion = { kind: "completed" },
  ): Promise<void> {
    this.#assertClaim(claim);
    const terminalCode = outcome.kind === "terminal" ? outcome.code : null;
    if (terminalCode !== null && !OUTCOME_CODE.test(terminalCode)) {
      throw new TypeError("terminal outcome code is invalid");
    }
    const completedAt = this.#completionNow();
    assertFiniteTime(completedAt, "completedAt");
    const db = await this.#db();
    const update = await db.runAsync(
      `UPDATE processed_intents
       SET state = ?, claim_token = NULL, claim_owner = NULL,
           lease_expires_at = NULL, completed_at = ?, terminal_code = ?
       WHERE message_id = ? AND state = 'claimed'
         AND claim_token = ? AND claim_owner = ?`,
      [
        outcome.kind,
        completedAt,
        terminalCode,
        claim.messageId,
        claim.token,
        claim.ownerId,
      ],
    );
    if (update.changes !== 1) throw new Error("notification claim is no longer owned");
  }

  async release(claim: ProcessedIntentClaim): Promise<void> {
    this.#assertClaim(claim);
    const db = await this.#db();
    await db.runAsync(
      `DELETE FROM processed_intents
       WHERE message_id = ? AND state = 'claimed'
         AND claim_token = ? AND claim_owner = ?`,
      [claim.messageId, claim.token, claim.ownerId],
    );
  }

  /** Persists safe terminal evidence for valid envelopes rejected before claim. */
  async recordTerminalUnclaimed(input: {
    messageId: string;
    code: string;
    completedAt: number;
  }): Promise<boolean> {
    assertOpaqueId(input.messageId, "messageId");
    if (!OUTCOME_CODE.test(input.code)) throw new TypeError("terminal outcome code is invalid");
    assertFiniteTime(input.completedAt, "completedAt");
    const db = await this.#db();
    const insert = await db.runAsync(
      `INSERT INTO processed_intents (
         message_id, state, completed_at, terminal_code
       ) VALUES (?, 'terminal', ?, ?)
       ON CONFLICT(message_id) DO NOTHING`,
      [input.messageId, input.completedAt, input.code],
    );
    return insert.changes === 1;
  }

  async inspectLedger(): Promise<NotificationLedgerEntry[]> {
    const db = await this.#db();
    const rows = await db.getAllAsync<NotificationIntentRow>(
      "SELECT * FROM processed_intents ORDER BY message_id",
    );
    return rows.map((row) => {
      if (!(row.state === "claimed" || row.state === "completed" || row.state === "terminal")) {
        throw new Error("notification ledger contains an unknown state");
      }
      return {
        messageId: row.message_id,
        state: row.state,
        leaseExpiresAt: row.lease_expires_at ?? undefined,
        completedAt: row.completed_at ?? undefined,
        terminalCode: row.terminal_code ?? undefined,
      };
    });
  }

  async automaticSyncEnabled(): Promise<boolean> {
    const db = await this.#db();
    const row = await db.getFirstAsync<{ setting_value: string }>(
      `SELECT setting_value FROM lifecycle_settings
       WHERE setting_key = 'automatic_sync_enabled'`,
    );
    if (row === null || !(row.setting_value === "0" || row.setting_value === "1")) {
      throw new Error("automatic sync setting is missing or corrupt");
    }
    return row.setting_value === "1";
  }

  /** Stage 05 production boundary only permits cleanup back to disabled. */
  async disableAutomaticSync(): Promise<void> {
    const db = await this.#db();
    const update = await db.runAsync(
      `UPDATE lifecycle_settings SET setting_value = ?
       WHERE setting_key = 'automatic_sync_enabled'`,
      ["0"],
    );
    if (update.changes !== 1) throw new Error("automatic sync disable state was not stored");
  }

  async #db(): Promise<SQLiteDatabase> {
    return this.#repository.databaseForSyncAdapter();
  }

  #assertClaim(claim: ProcessedIntentClaim): void {
    assertOpaqueId(claim.messageId, "claim.messageId");
    assertOpaqueId(claim.token, "claim.token");
    assertOpaqueId(claim.ownerId, "claim.ownerId");
    assertFiniteTime(claim.expiresAt, "claim.expiresAt");
  }
}
