import type { SyncOpportunityResult } from "@field-notes/lifecycle-engine";

export type BackgroundRuntimePort = {
  repository: { ready(): Promise<void> };
  run(
    trigger: "background",
    options: { deadlineAt: number; signal: AbortSignal },
  ): Promise<SyncOpportunityResult>;
};

/**
 * A background invocation is successful only when every claimed command has a
 * durable checkpoint. Registration or transport completion alone is not proof.
 */
export async function runBackgroundSync(input: {
  runtime: BackgroundRuntimePort;
  signal: AbortSignal;
  deadlineAt: number;
  automaticSyncEnabled?: () => Promise<boolean>;
}): Promise<{
  kind: "durable" | "failed" | "disabled";
  claimed: number;
  checkpoints: number;
}> {
  await input.runtime.repository.ready();
  if (input.automaticSyncEnabled !== undefined && !(await input.automaticSyncEnabled())) {
    return { kind: "disabled", claimed: 0, checkpoints: 0 };
  }
  const result = await input.runtime.run("background", {
    deadlineAt: input.deadlineAt,
    signal: input.signal,
  });
  const execution = result.kind === "coalesced" ? result.execution : result;
  if (execution.kind !== "ran") {
    return { kind: "failed", claimed: 0, checkpoints: 0 };
  }
  const worker = execution.worker;
  const durable =
    worker.stopped !== "aborted" &&
    worker.stopped !== "checkpoint-failed" &&
    worker.checkpoints.length === worker.claimed;
  return {
    kind: durable ? "durable" : "failed",
    claimed: worker.claimed,
    checkpoints: worker.checkpoints.length,
  };
}

export function backgroundInvocationSucceeded(
  result: { kind: "durable" | "failed" | "disabled" },
): boolean {
  return result.kind !== "failed";
}
