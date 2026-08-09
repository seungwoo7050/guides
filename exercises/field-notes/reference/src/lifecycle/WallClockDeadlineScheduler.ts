import type { DeadlineScheduler } from "../../../lifecycle-engine/src/ports.ts";

export interface WallClockTimerApi<Handle> {
  now(): number;
  setTimeout(callback: () => void, delayMs: number): Handle;
  clearTimeout(handle: Handle): void;
}

export type WallClockDeadlineError = {
  kind: "invalid-clock";
  phase: "timer-callback";
};

const MAX_TIMER_DELAY_MS = 2_147_483_647;

/** Wall-clock deadline adapter with idempotent cancellation and disposal. */
export class WallClockDeadlineScheduler<Handle> implements DeadlineScheduler {
  readonly #timers: WallClockTimerApi<Handle>;
  readonly #onError: (error: WallClockDeadlineError) => void;
  readonly #cancellations = new Set<() => void>();

  constructor(
    timers: WallClockTimerApi<Handle>,
    onError: (error: WallClockDeadlineError) => void = () => undefined,
  ) {
    this.#timers = timers;
    this.#onError = onError;
  }

  schedule(at: number, callback: () => void): () => void {
    if (!Number.isFinite(at)) {
      throw new RangeError("deadline must be finite");
    }

    let handle: Handle | undefined;
    let cancelled = false;
    let cancel!: () => void;

    const arm = (): void => {
      if (cancelled) return;
      const now = this.#timers.now();
      if (!Number.isFinite(now)) {
        cancel();
        throw new RangeError("wall clock must be finite");
      }
      const remaining = Math.max(0, at - now);
      handle = this.#timers.setTimeout(
        () => {
          handle = undefined;
          if (cancelled) return;
          const callbackNow = this.#timers.now();
          if (!Number.isFinite(callbackNow)) {
            cancelled = true;
            this.#cancellations.delete(cancel);
            this.#reportError({
              kind: "invalid-clock",
              phase: "timer-callback",
            });
            return;
          }
          if (callbackNow < at) {
            arm();
            return;
          }
          cancelled = true;
          this.#cancellations.delete(cancel);
          callback();
        },
        Math.min(remaining, MAX_TIMER_DELAY_MS),
      );
    };

    cancel = () => {
      if (cancelled) return;
      cancelled = true;
      if (handle !== undefined) {
        this.#timers.clearTimeout(handle);
        handle = undefined;
      }
      this.#cancellations.delete(cancel);
    };
    this.#cancellations.add(cancel);
    arm();
    return cancel;
  }

  dispose(): void {
    for (const cancel of [...this.#cancellations]) cancel();
  }

  pendingCount(): number {
    return this.#cancellations.size;
  }

  #reportError(error: WallClockDeadlineError): void {
    try {
      this.#onError(error);
    } catch {
      // Diagnostic observation must not resurrect or fire a cancelled deadline.
    }
  }
}

export function createSystemWallClockDeadlineScheduler(): WallClockDeadlineScheduler<
  ReturnType<typeof globalThis.setTimeout>
> {
  return new WallClockDeadlineScheduler({
    now: () => Date.now(),
    setTimeout: (callback, delayMs) => globalThis.setTimeout(callback, delayMs),
    clearTimeout: (handle) => globalThis.clearTimeout(handle),
  });
}
