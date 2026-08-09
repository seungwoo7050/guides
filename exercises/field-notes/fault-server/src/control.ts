type Waiter = {
  dueAt: number;
  sequence: number;
  resolve: () => void;
};

/**
 * A clock whose sleepers advance only when the test calls advanceBy/advanceTo.
 * It never delegates to setTimeout, so delay and response reorder tests do not
 * depend on wall-clock timing.
 */
export class ManualClock {
  readonly #waiters: Waiter[] = [];
  #now: number;
  #sequence = 0;

  constructor(initialTime = 0) {
    if (!Number.isFinite(initialTime)) {
      throw new TypeError("initialTime must be finite");
    }
    this.#now = initialTime;
  }

  now(): number {
    return this.#now;
  }

  pendingCount(): number {
    return this.#waiters.length;
  }

  sleep(milliseconds: number): Promise<void> {
    if (!Number.isFinite(milliseconds) || milliseconds < 0) {
      return Promise.reject(new RangeError("delay must be a non-negative finite number"));
    }
    if (milliseconds === 0) {
      return Promise.resolve();
    }

    return new Promise<void>((resolve) => {
      this.#waiters.push({
        dueAt: this.#now + milliseconds,
        sequence: this.#sequence++,
        resolve,
      });
      this.#waiters.sort(
        (left, right) => left.dueAt - right.dueAt || left.sequence - right.sequence,
      );
    });
  }

  advanceBy(milliseconds: number): void {
    if (!Number.isFinite(milliseconds) || milliseconds < 0) {
      throw new RangeError("advanceBy requires a non-negative finite number");
    }
    this.advanceTo(this.#now + milliseconds);
  }

  advanceTo(time: number): void {
    if (!Number.isFinite(time) || time < this.#now) {
      throw new RangeError("advanceTo cannot move the clock backwards");
    }
    this.#now = time;

    while (this.#waiters[0]?.dueAt !== undefined && this.#waiters[0].dueAt <= time) {
      const waiter = this.#waiters.shift();
      waiter?.resolve();
    }
  }

  reset(time = 0): void {
    if (this.#waiters.length > 0) {
      throw new Error("cannot reset ManualClock while controlled sleepers are pending");
    }
    if (!Number.isFinite(time)) {
      throw new TypeError("reset time must be finite");
    }
    this.#now = time;
    this.#sequence = 0;
  }
}
