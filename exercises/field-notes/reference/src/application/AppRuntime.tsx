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

type StorageStatus = "opening" | "ready" | "error";

type RuntimeServices = {
  repository: SQLiteFieldNotesRepository;
  attachments: AppOwnedAttachmentService;
  reconciler: StorageReconciler;
  features: DeviceFeatureCoordinator;
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
  revision: number;
  appState: AppStateStatus;
  storageStatus: StorageStatus;
  storageError: string | null;
  reconciliation: StorageReconciliationReport | null;
  capabilities: DeviceCapabilitySnapshot | null;
  lastMediaOutcome: MediaActionOutcome | null;
};

const RuntimeContext = createContext<RuntimeValue | null>(null);

function createServices(): RuntimeServices {
  const repository = new SQLiteFieldNotesRepository();
  const files = new ExpoAttachmentFileStore();
  const camera = new ExpoImagePickerCameraAdapter();
  const picker = new ExpoSystemPhotoPickerAdapter();
  const location = new ExpoForegroundLocationAdapter();
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
      revision,
      appState,
      storageStatus,
      storageError,
      reconciliation,
      capabilities,
      lastMediaOutcome,
    }),
    [
      appState,
      attachTestFile,
      capabilities,
      capturePhoto,
      deleteRecord,
      getRecord,
      inspectStorage,
      listAttachments,
      listOutbox,
      listRecords,
      lastMediaOutcome,
      measureLocation,
      newRecordId,
      reconcileStorage,
      reconciliation,
      repository,
      revision,
      pickPhoto,
      refreshCapabilities,
      saveRecord,
      storageError,
      storageStatus,
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
