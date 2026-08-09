import * as BackgroundTask from "expo-background-task";
import * as TaskManager from "expo-task-manager";
import { createProductionSyncRuntime } from "../sync/ProductionSyncRuntime";
import {
  backgroundInvocationSucceeded,
  runBackgroundSync,
} from "./BackgroundSyncPolicy";
import { SQLiteNotificationRepository } from "./SQLiteNotificationRepository";

export const FIELD_NOTES_BACKGROUND_SYNC_TASK =
  "field-notes-durable-sync-v1";
export const BACKGROUND_MINIMUM_INTERVAL_MINUTES = 15;
const BACKGROUND_BUDGET_MS = 25_000;

/** Module scope is required so headless launches define the task before React. */
TaskManager.defineTask(FIELD_NOTES_BACKGROUND_SYNC_TASK, async () => {
  const controller = new AbortController();
  let expiration: { remove(): void } | null = null;
  const runtime = createProductionSyncRuntime();
  try {
    expiration = BackgroundTask.addExpirationListener(() => {
      controller.abort("os-expiration");
    });
    const lifecycleState = new SQLiteNotificationRepository({
      repository: runtime.repository,
    });
    const result = await runBackgroundSync({
      runtime,
      signal: controller.signal,
      deadlineAt: Date.now() + BACKGROUND_BUDGET_MS,
      automaticSyncEnabled: () => lifecycleState.automaticSyncEnabled(),
    });
    return backgroundInvocationSucceeded(result)
      ? BackgroundTask.BackgroundTaskResult.Success
      : BackgroundTask.BackgroundTaskResult.Failed;
  } catch {
    return BackgroundTask.BackgroundTaskResult.Failed;
  } finally {
    expiration?.remove();
    runtime.dispose();
  }
});

export type BackgroundSyncRegistrationObservation = {
  availability: "available" | "restricted" | "error";
  registered: boolean;
};

export async function inspectBackgroundSyncRegistration(): Promise<
  BackgroundSyncRegistrationObservation
> {
  try {
    const status = await BackgroundTask.getStatusAsync();
    const registered = await TaskManager.isTaskRegisteredAsync(
      FIELD_NOTES_BACKGROUND_SYNC_TASK,
    );
    return {
      availability:
        status === BackgroundTask.BackgroundTaskStatus.Available
          ? "available"
          : "restricted",
      registered,
    };
  } catch {
    return { availability: "error", registered: false };
  }
}

/** Explicit user action; the interval is an OS-controlled minimum, not a schedule. */
export async function registerBackgroundSync(): Promise<
  BackgroundSyncRegistrationObservation
> {
  await BackgroundTask.registerTaskAsync(FIELD_NOTES_BACKGROUND_SYNC_TASK, {
    minimumInterval: BACKGROUND_MINIMUM_INTERVAL_MINUTES,
  });
  return inspectBackgroundSyncRegistration();
}

export async function unregisterBackgroundSync(): Promise<
  BackgroundSyncRegistrationObservation
> {
  await BackgroundTask.unregisterTaskAsync(FIELD_NOTES_BACKGROUND_SYNC_TASK);
  return inspectBackgroundSyncRegistration();
}
