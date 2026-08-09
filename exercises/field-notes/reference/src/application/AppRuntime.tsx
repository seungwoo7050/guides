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
  BoundedSyncWorker,
  FixedSyncBudget,
  type ConflictResolutionResult,
  type RepositorySnapshot,
  type WorkerRunResult,
} from "@field-notes/sync-engine";
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
import { AppState, type AppStateStatus } from "react-native";
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
import { AppOwnedAttachmentService } from "../storage/AppOwnedAttachmentService";
import { ExpoAttachmentFileStore } from "../storage/ExpoAttachmentFileStore";
import { productionClock, productionIds } from "../storage/productionIdentity";
import { SQLiteFieldNotesRepository } from "../storage/SQLiteFieldNotesRepository";
import { StorageReconciler } from "../storage/StorageReconciler";
import {
  configuredSyncEndpoint,
  FetchSyncTransport,
} from "../sync/FetchSyncTransport";
import { SQLiteSyncRepositoryAdapter } from "../sync/SQLiteSyncRepositoryAdapter";

type StorageStatus = "opening" | "ready" | "error";

type RuntimeServices = {
  repository: SQLiteFieldNotesRepository;
  attachments: AppOwnedAttachmentService;
  reconciler: StorageReconciler;
  features: DeviceFeatureCoordinator;
  syncRepository: SQLiteSyncRepositoryAdapter;
  syncWorker: BoundedSyncWorker;
  syncEndpoint: string;
};

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
  resumeBlockedAuth(): Promise<number>;
  resolveConflict(
    conflictId: string,
    choice: "remote" | "local",
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
};

const RuntimeContext = createContext<RuntimeValue | null>(null);

function createServices(): RuntimeServices {
  const repository = new SQLiteFieldNotesRepository();
  const files = new ExpoAttachmentFileStore();
  const camera = new ExpoImagePickerCameraAdapter();
  const picker = new ExpoSystemPhotoPickerAdapter();
  const location = new ExpoForegroundLocationAdapter();
  const syncRepository = new SQLiteSyncRepositoryAdapter(repository);
  const syncClock = { now: () => Date.now() };
  const syncEndpoint = configuredSyncEndpoint();
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
    syncRepository,
    syncWorker: new BoundedSyncWorker({
      repository: syncRepository,
      transport: new FetchSyncTransport({ endpoint: syncEndpoint }),
      clock: syncClock,
      budget: new FixedSyncBudget({
        maxCommands: 10,
        leaseDurationMs: 30_000,
        retryDelayMs: 5_000,
        maxAttempts: 5,
      }),
    }),
    syncEndpoint,
  };
}

export function AppRuntimeProvider({ children }: PropsWithChildren) {
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
  const activeSyncRun = useRef<Promise<WorkerRunResult> | null>(null);

  const reconcileStorage = useCallback(async () => {
    await repository.ready();
    const report = await services.reconciler.reconcile();
    setReconciliation(report);
    setRevision((value) => value + 1);
    return report;
  }, [repository, services.reconciler]);

  const refreshCapabilities = useCallback(async () => {
    const snapshot = await services.features.inspectCapabilities();
    setCapabilities(snapshot);
    return snapshot;
  }, [services.features]);

  const recoverMedia = useCallback(async () => {
    const outcome = await services.features.recoverPendingMedia();
    if (outcome.kind !== "none") setLastMediaOutcome(outcome);
    if (outcome.kind === "attached") setRevision((value) => value + 1);
    return outcome;
  }, [services.features]);

  useEffect(() => {
    let active = true;
    void (async () => {
      await repository.ready();
      await recoverMedia();
      const report = await services.reconciler.reconcile();
      const capabilitySnapshot = await services.features.inspectCapabilities();
      return { report, capabilitySnapshot };
    })()
      .then(({ report, capabilitySnapshot }) => {
        if (!active) return;
        setReconciliation(report);
        setCapabilities(capabilitySnapshot);
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
  }, [recoverMedia, repository, services.features, services.reconciler]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      setAppState(nextState);
      if (nextState !== "active") {
        services.features.invalidateLocationMeasurement();
      }
      if (nextState === "active" && storageStatus === "ready") {
        void (async () => {
          await refreshCapabilities();
          await recoverMedia();
          await reconcileStorage();
        })().catch((error: unknown) => {
          setStorageError(`app-active reconciliation failed: ${String(error)}`);
        });
      }
    });
    return () => subscription.remove();
  }, [reconcileStorage, recoverMedia, refreshCapabilities, services.features, storageStatus]);

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
      await repository.deleteWithCommand({ id, expectedLocalRevision });
      setRevision((value) => value + 1);
      void reconcileStorage().catch((error: unknown) => {
        setStorageError(`attachment cleanup failed: ${String(error)}`);
      });
    },
    [reconcileStorage, repository],
  );
  const listAttachments = useCallback(
    (recordId: string) => repository.listAttachments(recordId),
    [repository],
  );
  const attachTestFile = useCallback(
    async (recordId: string) => {
      const attachment = await services.attachments.attachNonSensitiveTestFile(recordId);
      setRevision((value) => value + 1);
      return attachment;
    },
    [services.attachments],
  );
  const listOutbox = useCallback(() => repository.listOutbox(), [repository]);
  const inspectStorage = useCallback(() => repository.snapshot(), [repository]);
  const newRecordId = useCallback(() => productionIds.recordId(), []);
  const capturePhoto = useCallback(
    async (recordId: string) => {
      const outcome = await services.features.capturePhoto(recordId);
      setLastMediaOutcome(outcome);
      await refreshCapabilities();
      if (outcome.kind === "attached") setRevision((value) => value + 1);
      if (outcome.kind === "failed") void reconcileStorage().catch(() => undefined);
      return outcome;
    },
    [reconcileStorage, refreshCapabilities, services.features],
  );
  const pickPhoto = useCallback(
    async (recordId: string) => {
      const outcome = await services.features.pickPhoto(recordId);
      setLastMediaOutcome(outcome);
      await refreshCapabilities();
      if (outcome.kind === "attached") setRevision((value) => value + 1);
      if (outcome.kind === "failed") void reconcileStorage().catch(() => undefined);
      return outcome;
    },
    [reconcileStorage, refreshCapabilities, services.features],
  );
  const measureLocation = useCallback(async () => {
    const outcome = await services.features.measureLocation();
    await refreshCapabilities();
    return outcome;
  }, [refreshCapabilities, services.features]);
  const inspectSync = useCallback(
    () => services.syncRepository.snapshot(),
    [services.syncRepository],
  );
  const runManualSync = useCallback(() => {
    if (activeSyncRun.current !== null) return activeSyncRun.current;
    setSyncRunning(true);
    const run = services.syncWorker.run({
      trigger: "manual",
      workerId: `manual-${Date.now().toString(36)}`,
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
  }, [services.syncWorker]);
  const resumeBlockedAuth = useCallback(async () => {
    const resumed = await services.syncRepository.resumeBlockedAuth(Date.now());
    setRevision((current) => current + 1);
    return resumed;
  }, [services.syncRepository]);
  const resolveConflict = useCallback(
    async (conflictId: string, choice: "remote" | "local") => {
      const now = Date.now();
      const resolution = choice === "remote"
        ? { kind: "remote" as const, resolvedAt: now }
        : {
            kind: "local" as const,
            commandId: productionIds.commandId(),
            createdAt: new Date(now).toISOString(),
            resolvedAt: now,
          };
      const result = await services.syncRepository.resolveConflict(
        conflictId,
        resolution,
      );
      setRevision((current) => current + 1);
      return result;
    },
    [services.syncRepository],
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
    }),
    [
      appState,
      attachTestFile,
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
      refreshCapabilities,
      resolveConflict,
      resumeBlockedAuth,
      runManualSync,
      saveRecord,
      storageError,
      storageStatus,
      services.syncEndpoint,
      syncRunning,
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
