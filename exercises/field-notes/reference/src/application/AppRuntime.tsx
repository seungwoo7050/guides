import type {
  Attachment,
  FieldRecord,
  LocalDatabaseSnapshot,
  OutboxEntry,
  RecordPayload,
  RecordRepository,
  StorageReconciliationReport,
} from "@field-notes/shared";
import {
  AndroidNotificationRegistrationCoordinator,
  NotificationIntentCoordinator,
  type AndroidNotificationRegistrationResult,
  type NotificationNavigationIntent,
} from "@field-notes/lifecycle-engine";
import {
  type ConflictResolutionResult,
  type RepositorySnapshot,
  type WorkerRunResult,
} from "@field-notes/sync-engine";
import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { useRouter } from "expo-router";
import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AppState, Platform, type AppStateStatus } from "react-native";
import {
  DeviceFeatureCoordinator,
  type DeviceCapabilitySnapshot,
  type LocationActionOutcome,
  type MediaActionOutcome,
} from "../device/DeviceFeatureCoordinator";
import {
  ExpoImagePickerCameraAdapter,
  ExpoPendingImagePickerResultAdapter,
  ExpoSystemPhotoPickerAdapter,
} from "../device/ExpoImagePickerAdapters";
import { ExpoForegroundLocationAdapter } from "../device/ExpoForegroundLocationAdapter";
import {
  ExpoAndroidNotificationChannelAdapter,
  ExpoAndroidNotificationPermissionAdapter,
  ExpoPushTokenAdapter,
} from "../lifecycle/AndroidNotificationAdapters";
import {
  inspectBackgroundSyncRegistration,
  registerBackgroundSync,
  unregisterBackgroundSync,
  type BackgroundSyncRegistrationObservation,
} from "../lifecycle/backgroundSyncTask";
import {
  expoNotificationResponseKey,
  SerializedExpoNotificationResponseSource,
  type ExpoNotificationResponseApi,
} from "../lifecycle/ExpoNotificationResponseSource";
import { NotificationResponseController } from "../lifecycle/NotificationResponseController";
import {
  SQLiteNotificationRepository,
} from "../lifecycle/SQLiteNotificationRepository";
import { AppOwnedAttachmentService } from "../storage/AppOwnedAttachmentService";
import {
  applyReservedRoute,
  CrossSourceRouteArbiter,
} from "../navigation/CrossSourceRouteArbiter";
import { ExpoAttachmentFileStore } from "../storage/ExpoAttachmentFileStore";
import { productionClock, productionIds } from "../storage/productionIdentity";
import { SQLiteFieldNotesRepository } from "../storage/SQLiteFieldNotesRepository";
import { StorageReconciler } from "../storage/StorageReconciler";
import {
  createProductionSyncRuntime,
  nextProductionNotificationClaimToken,
  observedWorkerRun,
  type ProductionSyncRuntime,
} from "../sync/ProductionSyncRuntime";
import { SerializedForegroundPipeline } from "./SerializedForegroundPipeline";

type StorageStatus = "opening" | "ready" | "error";

type RuntimeServices = {
  repository: SQLiteFieldNotesRepository;
  attachments: AppOwnedAttachmentService;
  reconciler: StorageReconciler;
  features: DeviceFeatureCoordinator;
  syncRuntime: ProductionSyncRuntime;
  notifications: SQLiteNotificationRepository;
  notificationIntents: NotificationIntentCoordinator;
  navigationArbiter: CrossSourceRouteArbiter;
  syncEndpoint: string;
};

export type SafeNotificationRegistrationState =
  | { kind: "idle" }
  | { kind: "unsupported-platform" }
  | { kind: "permission-required" }
  | { kind: "permission-denied"; canAskAgain: boolean }
  | { kind: "channel-failed" | "permission-restricted" | "token-failed"; reason: string }
  | { kind: "token-ready"; permission: "granted" | "not-required" };

type RuntimeValue = {
  repository: RecordRepository;
  listRecords(): Promise<FieldRecord[]>;
  getRecord(id: string): Promise<FieldRecord | null>;
  saveRecord(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<FieldRecord>;
  deleteRecord(id: string, expectedLocalRevision: number): Promise<void>;
  listAttachments(recordId: string): Promise<Attachment[]>;
  attachTestFile(recordId: string): Promise<Attachment>;
  listOutbox(): Promise<OutboxEntry[]>;
  inspectStorage(): Promise<LocalDatabaseSnapshot>;
  newRecordId(): string;
  reconcileStorage(): Promise<StorageReconciliationReport>;
  capturePhoto(recordId: string): Promise<MediaActionOutcome>;
  pickPhoto(recordId: string): Promise<MediaActionOutcome>;
  measureLocation(): Promise<LocationActionOutcome>;
  refreshCapabilities(): Promise<DeviceCapabilitySnapshot>;
  inspectSync(): Promise<RepositorySnapshot>;
  runManualSync(): Promise<WorkerRunResult>;
  registerNotifications(): Promise<SafeNotificationRegistrationState>;
  refreshBackgroundRegistration(): Promise<BackgroundSyncRegistrationObservation>;
  registerBackgroundOpportunity(): Promise<BackgroundSyncRegistrationObservation>;
  unregisterBackgroundOpportunity(): Promise<BackgroundSyncRegistrationObservation>;
  retryPendingNotification(): Promise<void>;
  setDraftActive(active: boolean): void;
  resumeBlockedAuth(): Promise<number>;
  resolveConflict(
    conflictId: string,
    choice: "remote" | "local" | "merge",
    mergePayload?: RecordPayload,
  ): Promise<ConflictResolutionResult>;
  revision: number;
  appState: AppStateStatus;
  storageStatus: StorageStatus;
  storageError: string | null;
  reconciliation: StorageReconciliationReport | null;
  capabilities: DeviceCapabilitySnapshot | null;
  lastMediaOutcome: MediaActionOutcome | null;
  syncRunning: boolean;
  lastSyncRun: WorkerRunResult | null;
  syncEndpoint: string;
  notificationRegistration: SafeNotificationRegistrationState;
  backgroundRegistration: BackgroundSyncRegistrationObservation | null;
  pendingNotificationAction: boolean;
  navigationArbiter: CrossSourceRouteArbiter;
};

const RuntimeContext = createContext<RuntimeValue | null>(null);

function safeRegistrationResult(
  result: AndroidNotificationRegistrationResult,
): SafeNotificationRegistrationState {
  if (result.kind === "token-ready") {
    return { kind: "token-ready", permission: result.permission };
  }
  if (result.kind === "permission-denied") {
    return { kind: result.kind, canAskAgain: result.canAskAgain };
  }
  if (result.kind === "permission-required") return result;
  return { kind: result.kind, reason: result.reason };
}

function configuredExpoProjectId(): string | null {
  const direct = Constants.easConfig?.projectId;
  if (typeof direct === "string" && direct.length > 0) return direct;
  const extra = Constants.expoConfig?.extra as
    | { eas?: { projectId?: unknown } }
    | undefined;
  const nested = extra?.eas?.projectId;
  return typeof nested === "string" && nested.length > 0 ? nested : null;
}

function createServices(): RuntimeServices {
  const syncRuntime = createProductionSyncRuntime();
  const repository = syncRuntime.repository;
  const files = new ExpoAttachmentFileStore();
  const camera = new ExpoImagePickerCameraAdapter();
  const picker = new ExpoSystemPhotoPickerAdapter();
  const location = new ExpoForegroundLocationAdapter();
  const notificationRepository = new SQLiteNotificationRepository({
    repository,
    claimToken: nextProductionNotificationClaimToken,
    completionNow: Date.now,
  });
  const notificationIntents = new NotificationIntentCoordinator({
    repository: notificationRepository,
    claims: notificationRepository,
    clock: { now: Date.now },
    owners: {
      next: () => `notification-owner-${productionIds.commandId().slice(-48)}`,
    },
    claimLeaseMs: 30_000,
  });
  return {
    repository,
    attachments: new AppOwnedAttachmentService(repository, files),
    reconciler: new StorageReconciler(repository, files),
    features: new DeviceFeatureCoordinator(
      camera,
      picker,
      location,
      new ExpoPendingImagePickerResultAdapter(),
      repository,
      files,
      productionClock,
      productionIds,
    ),
    syncRuntime,
    notifications: notificationRepository,
    notificationIntents,
    navigationArbiter: new CrossSourceRouteArbiter(),
    syncEndpoint: syncRuntime.endpoint,
  };
}

export function AppRuntimeProvider({ children }: PropsWithChildren) {
  const router = useRouter();
  const servicesRef = useRef<RuntimeServices | null>(null);
  servicesRef.current ??= createServices();
  const services = servicesRef.current;
  const repository = services.repository;
  const [revision, setRevision] = useState(0);
  const [appState, setAppState] = useState<AppStateStatus>(AppState.currentState);
  const [storageStatus, setStorageStatus] = useState<StorageStatus>("opening");
  const [storageError, setStorageError] = useState<string | null>(null);
  const [reconciliation, setReconciliation] =
    useState<StorageReconciliationReport | null>(null);
  const [capabilities, setCapabilities] =
    useState<DeviceCapabilitySnapshot | null>(null);
  const [lastMediaOutcome, setLastMediaOutcome] =
    useState<MediaActionOutcome | null>(null);
  const [syncRunning, setSyncRunning] = useState(false);
  const [lastSyncRun, setLastSyncRun] = useState<WorkerRunResult | null>(null);
  const [notificationRegistration, setNotificationRegistration] =
    useState<SafeNotificationRegistrationState>({ kind: "idle" });
  const [backgroundRegistration, setBackgroundRegistration] =
    useState<BackgroundSyncRegistrationObservation | null>(null);
  const [pendingNotificationAction, setPendingNotificationAction] = useState(false);
  const activeSyncRun = useRef<Promise<WorkerRunResult> | null>(null);
  const foregroundPipeline = useRef(new SerializedForegroundPipeline()).current;
  const draftActive = useRef(false);
  const notificationSource = useRef<
    SerializedExpoNotificationResponseSource<Notifications.NotificationResponse> | null
  >(null);

  const setDraftActive = useCallback((active: boolean) => {
    draftActive.current = active;
  }, []);

  const reconcileStorageUnserialized = useCallback(async () => {
    await repository.ready();
    const report = await services.reconciler.reconcile();
    setReconciliation(report);
    setRevision((value) => value + 1);
    return report;
  }, [repository, services.reconciler]);

  const reconcileStorage = useCallback(
    () => foregroundPipeline.run(reconcileStorageUnserialized),
    [foregroundPipeline, reconcileStorageUnserialized],
  );

  const refreshCapabilities = useCallback(async () => {
    const snapshot = await services.features.inspectCapabilities();
    setCapabilities(snapshot);
    return snapshot;
  }, [services.features]);

  const recoverMediaUnserialized = useCallback(async () => {
    const outcome = await services.features.recoverPendingMedia();
    if (outcome.kind !== "none") setLastMediaOutcome(outcome);
    if (outcome.kind === "attached") setRevision((value) => value + 1);
    return outcome;
  }, [services.features]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await repository.ready();
      const report = await foregroundPipeline.run(async () => {
        await recoverMediaUnserialized();
        return reconcileStorageUnserialized();
      });
      const capabilitySnapshot = await services.features.inspectCapabilities();
      const background = await inspectBackgroundSyncRegistration();
      return { report, capabilitySnapshot, background };
    })()
      .then(({ report, capabilitySnapshot, background }) => {
        if (!active) return;
        setReconciliation(report);
        setCapabilities(capabilitySnapshot);
        setBackgroundRegistration(background);
        setStorageStatus("ready");
        setStorageError(null);
        setRevision((value) => value + 1);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setStorageStatus("error");
        setStorageError(String(error));
      });
    return () => {
      active = false;
    };
  }, [foregroundPipeline, recoverMediaUnserialized, reconcileStorageUnserialized, repository, services.features]);

  useEffect(() => {
    const navigate = async (intent: NotificationNavigationIntent) => {
      const reservation = services.navigationArbiter.reserveNotification(intent);
      if (reservation === null) return;
      applyReservedRoute(reservation, () => {
        if (intent.kind === "open-record") {
          router.push(`/records/${encodeURIComponent(intent.recordId)}`);
        } else if (intent.kind === "open-sync") {
          const suffix = intent.recordId === undefined
            ? `focus=${intent.focus}`
            : `focus=${intent.focus}&recordId=${encodeURIComponent(intent.recordId)}`;
          router.push(`/sync?${suffix}`);
        } else {
          router.push("/records");
        }
      });
    };
    const handler = new NotificationResponseController<Notifications.NotificationResponse>({
      coordinator: services.notificationIntents,
      ledger: services.notifications,
      draftActive: () => draftActive.current,
      navigate,
      onPending: setPendingNotificationAction,
    });
    const source = new SerializedExpoNotificationResponseSource({
      api: Notifications as unknown as ExpoNotificationResponseApi<Notifications.NotificationResponse>,
      handler,
      keyOf: expoNotificationResponseKey,
      onResult: (result) => {
        if (
          result.kind === "retryable" ||
          result.kind === "handler-error" ||
          result.kind === "clear-error"
        ) {
          setPendingNotificationAction(true);
        } else if (result.kind === "acknowledged" || result.kind === "terminal") {
          setPendingNotificationAction(false);
        }
      },
    });
    notificationSource.current = source;
    void source.start()
      .then((result) => {
        if (result.kind === "source-error") {
          setPendingNotificationAction(true);
          setStorageError(`notification response source unavailable: ${result.stage}`);
        }
      })
      .catch(() => {
        setPendingNotificationAction(true);
        setStorageError("notification response source could not start safely");
      });
    return () => {
      source.stop();
      if (notificationSource.current === source) notificationSource.current = null;
    };
  }, [router, services.navigationArbiter, services.notificationIntents, services.notifications]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      setAppState(nextState);
      if (nextState !== "active") {
        services.features.invalidateLocationMeasurement();
      }
      if (nextState === "active" && storageStatus === "ready") {
        void foregroundPipeline.run(async () => {
          await refreshCapabilities();
          await recoverMediaUnserialized();
          await reconcileStorageUnserialized();
        }).catch((error: unknown) => {
          setStorageError(`app-active reconciliation failed: ${String(error)}`);
        });
      }
    });
    return () => subscription.remove();
  }, [foregroundPipeline, reconcileStorageUnserialized, recoverMediaUnserialized, refreshCapabilities, services.features, storageStatus]);

  const listRecords = useCallback(() => repository.list(), [repository]);
  const getRecord = useCallback((id: string) => repository.get(id), [repository]);
  const saveRecord = useCallback(
    async (input: {
      id: string;
      expectedLocalRevision: number | null;
      payload: RecordPayload;
    }) => {
      const { record } = await repository.saveWithCommand(input);
      setRevision((value) => value + 1);
      return record;
    },
    [repository],
  );
  const deleteRecord = useCallback(
    async (id: string, expectedLocalRevision: number) => {
      await foregroundPipeline.run(async () => {
        await repository.deleteWithCommand({ id, expectedLocalRevision });
        setRevision((value) => value + 1);
        await reconcileStorageUnserialized();
      });
    },
    [foregroundPipeline, reconcileStorageUnserialized, repository],
  );
  const listAttachments = useCallback(
    (recordId: string) => repository.listAttachments(recordId),
    [repository],
  );
  const attachTestFile = useCallback(
    (recordId: string) => foregroundPipeline.run(async () => {
        const attachment = await services.attachments.attachNonSensitiveTestFile(recordId);
        setRevision((value) => value + 1);
        return attachment;
      }),
    [foregroundPipeline, services.attachments],
  );
  const listOutbox = useCallback(() => repository.listOutbox(), [repository]);
  const inspectStorage = useCallback(() => repository.snapshot(), [repository]);
  const newRecordId = useCallback(() => productionIds.recordId(), []);
  const capturePhoto = useCallback(
    (recordId: string) => foregroundPipeline.run(async () => {
        const outcome = await services.features.capturePhoto(recordId);
        setLastMediaOutcome(outcome);
        await refreshCapabilities();
        if (outcome.kind === "attached") setRevision((value) => value + 1);
        if (outcome.kind === "failed") {
          await reconcileStorageUnserialized().catch(() => undefined);
        }
        return outcome;
      }),
    [foregroundPipeline, reconcileStorageUnserialized, refreshCapabilities, services.features],
  );
  const pickPhoto = useCallback(
    (recordId: string) => foregroundPipeline.run(async () => {
        const outcome = await services.features.pickPhoto(recordId);
        setLastMediaOutcome(outcome);
        await refreshCapabilities();
        if (outcome.kind === "attached") setRevision((value) => value + 1);
        if (outcome.kind === "failed") {
          await reconcileStorageUnserialized().catch(() => undefined);
        }
        return outcome;
      }),
    [foregroundPipeline, reconcileStorageUnserialized, refreshCapabilities, services.features],
  );
  const measureLocation = useCallback(async () => {
    const outcome = await services.features.measureLocation();
    await refreshCapabilities();
    return outcome;
  }, [refreshCapabilities, services.features]);
  const inspectSync = useCallback(
    () => services.syncRuntime.syncRepository.snapshot(),
    [services.syncRuntime.syncRepository],
  );
  const runManualSync = useCallback(() => {
    if (activeSyncRun.current !== null) return activeSyncRun.current;
    setSyncRunning(true);
    const run = services.syncRuntime.run("manual", {
      deadlineAt: Date.now() + 20_000,
    }).then((opportunity) => {
      const worker = observedWorkerRun(opportunity);
      if (worker === null) throw new Error("manual sync opportunity did not start");
      return worker;
    });
    activeSyncRun.current = run;
    void run
      .then((value) => {
        setLastSyncRun(value);
        setStorageError(
          value.stopped === "checkpoint-failed"
            ? `sync checkpoint failed: ${value.checkpointError ?? "unknown"}`
            : null,
        );
        setRevision((current) => current + 1);
      })
      .catch((error: unknown) => {
        setStorageError(`manual sync failed safely: ${String(error)}`);
      })
      .finally(() => {
        activeSyncRun.current = null;
        setSyncRunning(false);
      });
    return run;
  }, [services.syncRuntime]);
  const registerNotifications = useCallback(async () => {
    if (Platform.OS !== "android") {
      const result: SafeNotificationRegistrationState = { kind: "unsupported-platform" };
      setNotificationRegistration(result);
      return result;
    }
    const projectId = configuredExpoProjectId();
    const androidVersion = typeof Platform.Version === "number"
      ? Platform.Version
      : Number.parseInt(String(Platform.Version), 10);
    const coordinator = new AndroidNotificationRegistrationCoordinator({
      channels: new ExpoAndroidNotificationChannelAdapter({
        api: Notifications,
        channelId: "field-notes-sync",
        channel: {
          name: "Field Notes sync",
          importance: Notifications.AndroidImportance.HIGH,
        },
      }),
      permissions: new ExpoAndroidNotificationPermissionAdapter({
        api: Notifications,
        runtimePermissionRequired: Number.isFinite(androidVersion) && androidVersion >= 33,
      }),
      // A missing EAS project must not skip the Android 13 channel/permission
      // path. It becomes a bounded token-stage failure after permission has
      // been decided, and no project identity is invented by this reference.
      tokens: projectId === null
        ? {
            getToken: async () => ({
              kind: "failed" as const,
              reason: "project-id-unavailable",
            }),
          }
        : new ExpoPushTokenAdapter({ api: Notifications, projectId }),
    });
    const result = safeRegistrationResult(
      await coordinator.register({ requestPermission: true }),
    );
    setNotificationRegistration(result);
    return result;
  }, []);
  const refreshBackgroundRegistration = useCallback(async () => {
    const result = await inspectBackgroundSyncRegistration();
    setBackgroundRegistration(result);
    return result;
  }, []);
  const registerBackgroundOpportunity = useCallback(async () => {
    const result = await registerBackgroundSync();
    setBackgroundRegistration(result);
    return result;
  }, []);
  const unregisterBackgroundOpportunity = useCallback(async () => {
    await services.notifications.disableAutomaticSync();
    const result = await unregisterBackgroundSync();
    setBackgroundRegistration(result);
    return result;
  }, [services.notifications]);
  const retryPendingNotification = useCallback(async () => {
    const source = notificationSource.current;
    const response = Notifications.getLastNotificationResponse();
    if (source === null || response === null) return;
    await source.enqueue("warm", response);
  }, []);
  const resumeBlockedAuth = useCallback(async () => {
    const resumed = await services.syncRuntime.syncRepository.resumeBlockedAuth(Date.now());
    setRevision((current) => current + 1);
    return resumed;
  }, [services.syncRuntime.syncRepository]);
  const resolveConflict = useCallback(
    async (
      conflictId: string,
      choice: "remote" | "local" | "merge",
      mergePayload?: RecordPayload,
    ) => {
      const now = Date.now();
      if (choice === "merge" && mergePayload === undefined) {
        throw new Error("merge resolution requires a payload");
      }
      const resolution = choice === "remote"
        ? { kind: "remote" as const, resolvedAt: now }
        : choice === "local"
          ? {
            kind: "local" as const,
            commandId: productionIds.commandId(),
            createdAt: new Date(now).toISOString(),
            resolvedAt: now,
          }
          : {
              kind: "merge" as const,
              commandId: productionIds.commandId(),
              payload: mergePayload!,
              createdAt: new Date(now).toISOString(),
              resolvedAt: now,
            };
      const result = await services.syncRuntime.syncRepository.resolveConflict(
        conflictId,
        resolution,
      );
      setRevision((current) => current + 1);
      return result;
    },
    [services.syncRuntime.syncRepository],
  );

  const value = useMemo<RuntimeValue>(
    () => ({
      repository,
      listRecords,
      getRecord,
      saveRecord,
      deleteRecord,
      listAttachments,
      attachTestFile,
      listOutbox,
      inspectStorage,
      newRecordId,
      reconcileStorage,
      capturePhoto,
      pickPhoto,
      measureLocation,
      refreshCapabilities,
      inspectSync,
      runManualSync,
      registerNotifications,
      refreshBackgroundRegistration,
      registerBackgroundOpportunity,
      unregisterBackgroundOpportunity,
      retryPendingNotification,
      setDraftActive,
      resumeBlockedAuth,
      resolveConflict,
      revision,
      appState,
      storageStatus,
      storageError,
      reconciliation,
      capabilities,
      lastMediaOutcome,
      syncRunning,
      lastSyncRun,
      syncEndpoint: services.syncEndpoint,
      notificationRegistration,
      backgroundRegistration,
      pendingNotificationAction,
      navigationArbiter: services.navigationArbiter,
    }),
    [
      appState,
      attachTestFile,
      backgroundRegistration,
      capabilities,
      capturePhoto,
      deleteRecord,
      getRecord,
      inspectStorage,
      inspectSync,
      listAttachments,
      listOutbox,
      listRecords,
      lastMediaOutcome,
      lastSyncRun,
      measureLocation,
      newRecordId,
      reconcileStorage,
      reconciliation,
      repository,
      revision,
      pickPhoto,
      pendingNotificationAction,
      refreshCapabilities,
      refreshBackgroundRegistration,
      registerNotifications,
      resolveConflict,
      resumeBlockedAuth,
      runManualSync,
      saveRecord,
      setDraftActive,
      storageError,
      storageStatus,
      services.syncEndpoint,
      syncRunning,
      notificationRegistration,
      services.navigationArbiter,
      registerBackgroundOpportunity,
      unregisterBackgroundOpportunity,
      retryPendingNotification,
    ],
  );
  return <RuntimeContext.Provider value={value}>{children}</RuntimeContext.Provider>;
}

export function useAppRuntime(): RuntimeValue {
  const value = useContext(RuntimeContext);
  if (value === null) {
    throw new Error("useAppRuntime must be used inside AppRuntimeProvider");
  }
  return value;
}
