import type { SyncBudget, SyncClock, SyncRepository, SyncTransport } from "./ports.ts";
import { parseTransportResponse } from "./response-parser.ts";
import type {
  CheckpointOutcome,
  ParsedTransportResult,
  SyncTrigger,
  WorkerRunResult,
} from "./types.ts";

function errorReason(error: unknown): string {
  if (typeof error === "object" && error !== null) {
    const value = error as { code?: unknown; name?: unknown };
    if (typeof value.code === "string") {
      return `transport-unknown:${value.code}`;
    }
    if (typeof value.name === "string") {
      return `transport-unknown:${value.name}`;
    }
  }
  return "transport-unknown:Error";
}

function checkpointForParsed(
  parsed: ParsedTransportResult,
  input: {
    now: number;
    attempt: number;
    budget: SyncBudget;
  },
): CheckpointOutcome {
  switch (parsed.kind) {
    case "success":
      return { kind: "success", remote: parsed.remote, completedAt: input.now };
    case "conflict":
      return { kind: "conflict", remote: parsed.remote, createdAt: input.now };
    case "blocked_auth":
      return { kind: "blocked_auth", reason: parsed.reason };
    case "permanent":
      return { kind: "permanent", reason: parsed.reason };
    case "invalid_response": {
      const reason = `invalid-response:${parsed.reason}`;
      return {
        kind: "retry_wait",
        reason,
        nextAttemptAt:
          input.now + input.budget.retryDelayMs({ attempt: input.attempt, reason }),
      };
    }
  }
}

export class BoundedSyncWorker {
  readonly #repository: SyncRepository;
  readonly #transport: SyncTransport;
  readonly #clock: SyncClock;
  readonly #budget: SyncBudget;

  constructor(input: {
    repository: SyncRepository;
    transport: SyncTransport;
    clock: SyncClock;
    budget: SyncBudget;
  }) {
    this.#repository = input.repository;
    this.#transport = input.transport;
    this.#clock = input.clock;
    this.#budget = input.budget;
  }

  async run(input: {
    trigger: SyncTrigger;
    workerId: string;
    signal?: AbortSignal;
  }): Promise<WorkerRunResult> {
    const signal = input.signal ?? new AbortController().signal;
    const result: WorkerRunResult = {
      trigger: input.trigger,
      workerId: input.workerId,
      claimed: 0,
      checkpoints: [],
      stopped: "idle",
    };

    while (true) {
      if (signal.aborted) {
        result.stopped = "aborted";
        return result;
      }
      const now = this.#clock.now();
      if (!this.#budget.canStartNext({ claimed: result.claimed, now })) {
        result.stopped = "budget";
        return result;
      }

      const claim = await this.#repository.claimNext({
        workerId: input.workerId,
        now,
        leaseDurationMs: this.#budget.leaseDurationMs(),
      });
      if (claim === null) {
        result.stopped = "idle";
        return result;
      }
      result.claimed += 1;

      let outcome: CheckpointOutcome;
      try {
        const response = await this.#transport.send(claim.attempted, signal);
        const parsed = parseTransportResponse(response, {
          attempted: claim.attempted,
          knownRemoteVersion: claim.knownRemoteVersion,
        });
        outcome = checkpointForParsed(parsed, {
          now: this.#clock.now(),
          attempt: claim.attempt,
          budget: this.#budget,
        });
      } catch (error: unknown) {
        const reason = errorReason(error);
        const checkpointAt = this.#clock.now();
        outcome = {
          kind: "retry_wait",
          reason,
          nextAttemptAt:
            checkpointAt +
            this.#budget.retryDelayMs({ attempt: claim.attempt, reason }),
        };
      }

      try {
        const checkpoint = await this.#repository.checkpoint({ claim, outcome });
        result.checkpoints.push(checkpoint);
      } catch (error: unknown) {
        result.stopped = "checkpoint-failed";
        result.checkpointError = error instanceof Error ? error.message : "unknown checkpoint error";
        return result;
      }
    }
  }
}
