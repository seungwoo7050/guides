import type {
  BoundedWorkerPort,
  DeadlineScheduler,
  LifecycleClock,
  WorkerIdGenerator,
} from "./ports.ts";
import type {
  LifecycleSyncTrigger,
  SyncExecution,
  SyncOpportunityResult,
} from "./types.ts";

type ActiveExecution = {
  trigger: LifecycleSyncTrigger;
  promise: Promise<SyncExecution>;
};

export class LifecycleSyncCoordinator {
  readonly #worker: BoundedWorkerPort;
  readonly #clock: LifecycleClock;
  readonly #deadlines: DeadlineScheduler;
  readonly #workerIds: WorkerIdGenerator;
  #active: ActiveExecution | null = null;

  constructor(input: {
    worker: BoundedWorkerPort;
    clock: LifecycleClock;
    deadlines: DeadlineScheduler;
    workerIds: WorkerIdGenerator;
  }) {
    this.#worker = input.worker;
    this.#clock = input.clock;
    this.#deadlines = input.deadlines;
    this.#workerIds = input.workerIds;
  }

  async runOpportunity(
    trigger: LifecycleSyncTrigger,
    options: { deadlineAt?: number; signal?: AbortSignal } = {},
  ): Promise<SyncOpportunityResult> {
    if (options.signal?.aborted === true) {
      return { kind: "not-started", trigger, reason: "aborted" };
    }
    if (
      options.deadlineAt !== undefined &&
      options.deadlineAt <= this.#clock.now()
    ) {
      return { kind: "not-started", trigger, reason: "deadline" };
    }

    const active = this.#active;
    if (active !== null) {
      return {
        kind: "coalesced",
        trigger,
        leaderTrigger: active.trigger,
        execution: await active.promise,
      };
    }

    const promise = this.#execute(trigger, options);
    const execution: ActiveExecution = { trigger, promise };
    this.#active = execution;
    try {
      return await promise;
    } finally {
      if (this.#active === execution) {
        this.#active = null;
      }
    }
  }

  async #execute(
    trigger: LifecycleSyncTrigger,
    options: { deadlineAt?: number; signal?: AbortSignal },
  ): Promise<SyncExecution> {
    const controller = new AbortController();
    const abortFromParent = () => controller.abort("parent-aborted");
    options.signal?.addEventListener("abort", abortFromParent, { once: true });

    let cancelDeadline: (() => void) | undefined;
    if (options.deadlineAt !== undefined) {
      cancelDeadline = this.#deadlines.schedule(options.deadlineAt, () => {
        controller.abort("deadline");
      });
    }

    const workerId = this.#workerIds.next(trigger);
    try {
      const worker = await this.#worker.run({
        trigger,
        workerId,
        signal: controller.signal,
      });
      return { kind: "ran", trigger, workerId, worker };
    } finally {
      cancelDeadline?.();
      options.signal?.removeEventListener("abort", abortFromParent);
    }
  }
}
