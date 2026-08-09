import type {
  AndroidNotificationChannelPort,
  BoundedWorkerPort,
  DeadlineScheduler,
  LifecycleClock,
  NotificationOwnerIdGenerator,
  NotificationInstallationRegistryPort,
  NotificationPermissionPort,
  NotificationStateRepository,
  ProcessedIntentClaimPort,
  ProcessedIntentClaimResult,
  PushTokenPort,
  WorkerIdGenerator,
} from "./ports.ts";
import type {
  AccountReadinessState,
  BoundedWorkerObservation,
  ConflictReadinessState,
  InstallationRegistryRemoveResult,
  InstallationRegistryUpsertResult,
  LifecycleSyncTrigger,
  NotificationPermissionState,
  NotificationInstallationBinding,
  ProcessedIntentClaim,
  RecordReadinessState,
} from "./types.ts";

export class Deferred<Value> {
  readonly promise: Promise<Value>;
  readonly #resolve: (value: Value | PromiseLike<Value>) => void;
  readonly #reject: (reason?: unknown) => void;

  constructor() {
    let resolve!: (value: Value | PromiseLike<Value>) => void;
    let reject!: (reason?: unknown) => void;
    this.promise = new Promise<Value>((resolvePromise, rejectPromise) => {
      resolve = resolvePromise;
      reject = rejectPromise;
    });
    this.#resolve = resolve;
    this.#reject = reject;
  }

  resolve(value: Value): void {
    this.#resolve(value);
  }

  reject(reason?: unknown): void {
    this.#reject(reason);
  }
}

type ScheduledTask = {
  id: number;
  at: number;
  callback: () => void;
};

export class DeterministicClock implements LifecycleClock, DeadlineScheduler {
  #now: number;
  #nextTaskId = 1;
  readonly #tasks = new Map<number, ScheduledTask>();

  constructor(now = 0) {
    this.#now = now;
  }

  now(): number {
    return this.#now;
  }

  schedule(at: number, callback: () => void): () => void {
    const id = this.#nextTaskId;
    this.#nextTaskId += 1;
    this.#tasks.set(id, { id, at, callback });
    return () => {
      this.#tasks.delete(id);
    };
  }

  advanceBy(milliseconds: number): void {
    this.advanceTo(this.#now + milliseconds);
  }

  advanceTo(target: number): void {
    if (target < this.#now) {
      throw new Error("deterministic clock cannot move backwards");
    }
    while (true) {
      const next = [...this.#tasks.values()]
        .filter((task) => task.at <= target)
        .sort((left, right) => left.at - right.at || left.id - right.id)[0];
      if (next === undefined) break;
      this.#tasks.delete(next.id);
      this.#now = Math.max(this.#now, next.at);
      next.callback();
    }
    this.#now = target;
  }
}

export class SequentialWorkerIds implements WorkerIdGenerator {
  #sequence = 0;

  next(trigger: LifecycleSyncTrigger): string {
    this.#sequence += 1;
    return `${trigger}-${this.#sequence}`;
  }
}

export class SequentialNotificationOwnerIds
  implements NotificationOwnerIdGenerator
{
  #sequence = 0;

  next(messageId: string): string {
    this.#sequence += 1;
    return `notification-${this.#sequence}:${messageId}`;
  }
}

type StoredIntentClaim =
  | { kind: "claimed"; claim: ProcessedIntentClaim }
  | { kind: "processed"; completedBy: string };

export class InMemoryProcessedIntentClaims implements ProcessedIntentClaimPort {
  readonly #entries = new Map<string, StoredIntentClaim>();
  #sequence = 0;

  async claim(input: {
    messageId: string;
    ownerId: string;
    now: number;
    leaseDurationMs: number;
  }): Promise<ProcessedIntentClaimResult> {
    const current = this.#entries.get(input.messageId);
    if (current?.kind === "processed") {
      return { kind: "duplicate" };
    }
    if (current?.kind === "claimed" && current.claim.expiresAt > input.now) {
      return { kind: "busy" };
    }
    this.#sequence += 1;
    const claim: ProcessedIntentClaim = {
      messageId: input.messageId,
      token: `intent-claim-${this.#sequence}`,
      ownerId: input.ownerId,
      expiresAt: input.now + input.leaseDurationMs,
    };
    this.#entries.set(input.messageId, { kind: "claimed", claim });
    return { kind: "claimed", claim };
  }

  async complete(claim: ProcessedIntentClaim): Promise<void> {
    const current = this.#entries.get(claim.messageId);
    if (current?.kind !== "claimed" || current.claim.token !== claim.token) {
      throw new Error("intent claim is no longer owned");
    }
    this.#entries.set(claim.messageId, {
      kind: "processed",
      completedBy: claim.ownerId,
    });
  }

  async release(claim: ProcessedIntentClaim): Promise<void> {
    const current = this.#entries.get(claim.messageId);
    if (current?.kind === "claimed" && current.claim.token === claim.token) {
      this.#entries.delete(claim.messageId);
    }
  }

  state(messageId: string): "absent" | "claimed" | "processed" {
    return this.#entries.get(messageId)?.kind ?? "absent";
  }
}

export class DeterministicNotificationRepository
  implements NotificationStateRepository
{
  readonly calls: string[] = [];
  readonly #readyGate: Promise<void>;
  #ready = false;
  #account: AccountReadinessState;
  #syncBlocked = false;
  readonly #records = new Map<string, RecordReadinessState>();
  readonly #conflicts = new Map<string, ConflictReadinessState>();

  constructor(input: {
    account: AccountReadinessState;
    readyGate?: Promise<void>;
  }) {
    this.#account = input.account;
    this.#readyGate = input.readyGate ?? Promise.resolve();
  }

  async ready(): Promise<void> {
    this.calls.push("ready:start");
    await this.#readyGate;
    this.#ready = true;
    this.calls.push("ready:complete");
  }

  setAccount(account: AccountReadinessState): void {
    this.#account = account;
  }

  setRecord(recordId: string, state: RecordReadinessState): void {
    this.#records.set(recordId, state);
  }

  setConflict(recordId: string, state: ConflictReadinessState): void {
    this.#conflicts.set(recordId, state);
  }

  setSyncBlocked(blocked: boolean): void {
    this.#syncBlocked = blocked;
  }

  async currentAccount(): Promise<AccountReadinessState> {
    this.#assertReady();
    this.calls.push("account");
    return this.#account;
  }

  async recordState(recordId: string): Promise<RecordReadinessState> {
    this.#assertReady();
    this.calls.push(`record:${recordId}`);
    return this.#records.get(recordId) ?? "missing";
  }

  async conflictState(recordId: string): Promise<ConflictReadinessState> {
    this.#assertReady();
    this.calls.push(`conflict:${recordId}`);
    return this.#conflicts.get(recordId) ?? "missing";
  }

  async isSyncBlocked(): Promise<boolean> {
    this.#assertReady();
    this.calls.push("sync-blocked");
    return this.#syncBlocked;
  }

  #assertReady(): void {
    if (!this.#ready) {
      throw new Error("business state was read before repository readiness");
    }
  }
}

export type DeterministicCommandState =
  | { kind: "pending"; attempt: number }
  | {
      kind: "leased";
      attempt: number;
      token: string;
      owner: string;
      expiresAt: number;
    }
  | { kind: "retry-wait"; attempt: number; nextAttemptAt: number; reason: string }
  | { kind: "completed"; attempt: number };

export type DeterministicCommandClaim = {
  commandId: string;
  token: string;
  owner: string;
  expiresAt: number;
  attempt: number;
};

export class DeterministicCommandRepository {
  readonly #states = new Map<string, DeterministicCommandState>();
  #leaseSequence = 0;

  constructor(commandIds: readonly string[]) {
    for (const commandId of commandIds) {
      this.#states.set(commandId, { kind: "pending", attempt: 0 });
    }
  }

  claim(input: {
    workerId: string;
    now: number;
    leaseDurationMs: number;
  }): DeterministicCommandClaim | null {
    for (const [commandId, state] of this.#states) {
      const eligible =
        state.kind === "pending" ||
        (state.kind === "retry-wait" && state.nextAttemptAt <= input.now) ||
        (state.kind === "leased" && state.expiresAt <= input.now);
      if (!eligible) continue;
      this.#leaseSequence += 1;
      const attempt = state.attempt + 1;
      const claim: DeterministicCommandClaim = {
        commandId,
        token: `lease-${this.#leaseSequence}`,
        owner: input.workerId,
        expiresAt: input.now + input.leaseDurationMs,
        attempt,
      };
      this.#states.set(commandId, {
        kind: "leased",
        attempt,
        token: claim.token,
        owner: claim.owner,
        expiresAt: claim.expiresAt,
      });
      return claim;
    }
    return null;
  }

  complete(claim: DeterministicCommandClaim): void {
    this.#assertOwns(claim);
    this.#states.set(claim.commandId, {
      kind: "completed",
      attempt: claim.attempt,
    });
  }

  checkpointUnknown(
    claim: DeterministicCommandClaim,
    input: { nextAttemptAt: number; reason: string },
  ): void {
    this.#assertOwns(claim);
    this.#states.set(claim.commandId, {
      kind: "retry-wait",
      attempt: claim.attempt,
      nextAttemptAt: input.nextAttemptAt,
      reason: input.reason,
    });
  }

  snapshot(): Array<{ commandId: string; state: DeterministicCommandState }> {
    return [...this.#states].map(([commandId, state]) => ({ commandId, state }));
  }

  #assertOwns(claim: DeterministicCommandClaim): void {
    const state = this.#states.get(claim.commandId);
    if (
      state?.kind !== "leased" ||
      state.token !== claim.token ||
      state.owner !== claim.owner
    ) {
      throw new Error("worker no longer owns command lease");
    }
  }
}

async function waitForGateOrAbort(
  gate: Promise<void>,
  signal: AbortSignal,
): Promise<void> {
  if (signal.aborted) return;
  await new Promise<void>((resolve, reject) => {
    const aborted = () => resolve();
    signal.addEventListener("abort", aborted, { once: true });
    void gate.then(resolve, reject).finally(() => {
      signal.removeEventListener("abort", aborted);
    });
  });
}

export class DeterministicBoundedWorker implements BoundedWorkerPort {
  readonly calls: Array<{ trigger: LifecycleSyncTrigger; workerId: string }> = [];
  readonly #repository: DeterministicCommandRepository;
  readonly #clock: LifecycleClock;
  readonly #maxCommands: number;
  readonly #leaseDurationMs: number;
  readonly #retryDelayMs: number;
  readonly #pauseAfterClaim: Promise<void> | undefined;

  constructor(input: {
    repository: DeterministicCommandRepository;
    clock: LifecycleClock;
    maxCommands?: number;
    leaseDurationMs?: number;
    retryDelayMs?: number;
    pauseAfterClaim?: Promise<void>;
  }) {
    this.#repository = input.repository;
    this.#clock = input.clock;
    this.#maxCommands = input.maxCommands ?? 10;
    this.#leaseDurationMs = input.leaseDurationMs ?? 1_000;
    this.#retryDelayMs = input.retryDelayMs ?? 500;
    this.#pauseAfterClaim = input.pauseAfterClaim;
  }

  async run(input: {
    trigger: LifecycleSyncTrigger;
    workerId: string;
    signal?: AbortSignal;
  }): Promise<BoundedWorkerObservation> {
    this.calls.push({ trigger: input.trigger, workerId: input.workerId });
    const signal = input.signal ?? new AbortController().signal;
    const checkpoints: unknown[] = [];
    let claimed = 0;

    while (true) {
      if (signal.aborted) {
        return {
          trigger: input.trigger,
          workerId: input.workerId,
          claimed,
          checkpoints,
          stopped: "aborted",
        };
      }
      if (claimed >= this.#maxCommands) {
        return {
          trigger: input.trigger,
          workerId: input.workerId,
          claimed,
          checkpoints,
          stopped: "budget",
        };
      }
      const claim = this.#repository.claim({
        workerId: input.workerId,
        now: this.#clock.now(),
        leaseDurationMs: this.#leaseDurationMs,
      });
      if (claim === null) {
        return {
          trigger: input.trigger,
          workerId: input.workerId,
          claimed,
          checkpoints,
          stopped: "idle",
        };
      }
      claimed += 1;

      if (this.#pauseAfterClaim !== undefined) {
        await waitForGateOrAbort(this.#pauseAfterClaim, signal);
      }
      if (signal.aborted) {
        const nextAttemptAt = this.#clock.now() + this.#retryDelayMs;
        this.#repository.checkpointUnknown(claim, {
          nextAttemptAt,
          reason: "unknown-after-abort",
        });
        checkpoints.push({
          commandId: claim.commandId,
          outcome: "retry_wait",
          reason: "unknown-after-abort",
        });
        return {
          trigger: input.trigger,
          workerId: input.workerId,
          claimed,
          checkpoints,
          stopped: "aborted",
        };
      }

      this.#repository.complete(claim);
      checkpoints.push({ commandId: claim.commandId, outcome: "success" });
    }
  }
}

export class ScriptedAndroidChannel implements AndroidNotificationChannelPort {
  readonly calls: string[];
  result: Awaited<ReturnType<AndroidNotificationChannelPort["ensureChannel"]>>;

  constructor(
    calls: string[],
    result: Awaited<ReturnType<AndroidNotificationChannelPort["ensureChannel"]>> = {
      kind: "ready",
    },
  ) {
    this.calls = calls;
    this.result = result;
  }

  async ensureChannel(): Promise<
    Awaited<ReturnType<AndroidNotificationChannelPort["ensureChannel"]>>
  > {
    this.calls.push("channel");
    return this.result;
  }
}

export class ScriptedNotificationPermission implements NotificationPermissionPort {
  readonly calls: string[];
  currentState: NotificationPermissionState;
  requestState: NotificationPermissionState;

  constructor(input: {
    calls: string[];
    current: NotificationPermissionState;
    request?: NotificationPermissionState;
  }) {
    this.calls = input.calls;
    this.currentState = input.current;
    this.requestState = input.request ?? input.current;
  }

  async current(): Promise<NotificationPermissionState> {
    this.calls.push("permission:current");
    return this.currentState;
  }

  async request(): Promise<NotificationPermissionState> {
    this.calls.push("permission:request");
    return this.requestState;
  }
}

export class ScriptedPushToken implements PushTokenPort {
  readonly calls: string[];
  result: Awaited<ReturnType<PushTokenPort["getToken"]>>;

  constructor(
    calls: string[],
    result: Awaited<ReturnType<PushTokenPort["getToken"]>>,
  ) {
    this.calls = calls;
    this.result = result;
  }

  async getToken(): Promise<Awaited<ReturnType<PushTokenPort["getToken"]>>> {
    this.calls.push("token");
    return this.result;
  }
}

export type DeterministicInstallationRegistryCall =
  | {
      operation: "upsert";
      installationId: string;
      accountId: string;
      tokenLabel: string;
      updatedAt: number;
    }
  | {
      operation: "remove";
      installationId: string;
      accountId: string;
    };

type RegistryFailure = {
  operation: DeterministicInstallationRegistryCall["operation"];
  reason: string;
};

/**
 * Backend-free test double. Call logs use deterministic token labels rather
 * than token contents, so traces remain safe even if a caller supplies a
 * credential-shaped value by mistake.
 */
export class DeterministicNotificationInstallationRegistry
  implements NotificationInstallationRegistryPort
{
  readonly calls: DeterministicInstallationRegistryCall[] = [];
  readonly #bindings = new Map<string, NotificationInstallationBinding>();
  readonly #tokenLabels = new Map<string, string>();
  readonly #failures: RegistryFailure[] = [];

  failNext(
    operation: DeterministicInstallationRegistryCall["operation"],
    reason: string,
  ): void {
    this.#failures.push({ operation, reason });
  }

  async upsert(input: {
    installationId: string;
    accountId: string;
    token: string;
    updatedAt: number;
  }): Promise<InstallationRegistryUpsertResult> {
    this.calls.push({
      operation: "upsert",
      installationId: input.installationId,
      accountId: input.accountId,
      tokenLabel: this.#tokenLabel(input.token),
      updatedAt: input.updatedAt,
    });
    const failure = this.#takeFailure("upsert");
    if (failure !== undefined) {
      return { kind: "failed", reason: failure };
    }
    const previous = this.#bindings.get(input.installationId) ?? null;
    this.#bindings.set(input.installationId, structuredClone(input));
    return {
      kind: "stored",
      previous: previous === null ? null : structuredClone(previous),
    };
  }

  async remove(input: {
    installationId: string;
    accountId: string;
  }): Promise<InstallationRegistryRemoveResult> {
    this.calls.push({
      operation: "remove",
      installationId: input.installationId,
      accountId: input.accountId,
    });
    const failure = this.#takeFailure("remove");
    if (failure !== undefined) {
      return { kind: "failed", reason: failure };
    }
    const previous = this.#bindings.get(input.installationId);
    if (previous === undefined) {
      return { kind: "absent" };
    }
    if (previous.accountId !== input.accountId) {
      return {
        kind: "account-mismatch",
        boundAccountId: previous.accountId,
      };
    }
    this.#bindings.delete(input.installationId);
    return { kind: "removed", previous: structuredClone(previous) };
  }

  snapshot(): NotificationInstallationBinding[] {
    return [...this.#bindings.values()]
      .sort((left, right) => left.installationId.localeCompare(right.installationId))
      .map((binding) => structuredClone(binding));
  }

  #tokenLabel(token: string): string {
    const current = this.#tokenLabels.get(token);
    if (current !== undefined) return current;
    const label = `token#${this.#tokenLabels.size + 1}`;
    this.#tokenLabels.set(token, label);
    return label;
  }

  #takeFailure(
    operation: DeterministicInstallationRegistryCall["operation"],
  ): string | undefined {
    const index = this.#failures.findIndex(
      (failure) => failure.operation === operation,
    );
    if (index < 0) return undefined;
    return this.#failures.splice(index, 1)[0]?.reason;
  }
}
