import type { SyncBudget } from "./ports.ts";

export class FixedSyncBudget implements SyncBudget {
  readonly #maxCommands: number;
  readonly #leaseDuration: number;
  readonly #retryDelay: number;

  constructor(options: {
    maxCommands: number;
    leaseDurationMs: number;
    retryDelayMs: number;
  }) {
    if (!Number.isInteger(options.maxCommands) || options.maxCommands < 1) {
      throw new RangeError("maxCommands must be a positive integer");
    }
    if (!Number.isFinite(options.leaseDurationMs) || options.leaseDurationMs <= 0) {
      throw new RangeError("leaseDurationMs must be positive");
    }
    if (!Number.isFinite(options.retryDelayMs) || options.retryDelayMs < 0) {
      throw new RangeError("retryDelayMs must be non-negative");
    }
    this.#maxCommands = options.maxCommands;
    this.#leaseDuration = options.leaseDurationMs;
    this.#retryDelay = options.retryDelayMs;
  }

  canStartNext(input: { claimed: number; now: number }): boolean {
    return input.claimed < this.#maxCommands && Number.isFinite(input.now);
  }

  leaseDurationMs(): number {
    return this.#leaseDuration;
  }

  retryDelayMs(_input: { attempt: number; reason: string }): number {
    return this.#retryDelay;
  }
}
