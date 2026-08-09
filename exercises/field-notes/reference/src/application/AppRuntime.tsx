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
import { AppOwnedAttachmentService } from "../storage/AppOwnedAttachmentService";
import { ExpoAttachmentFileStore } from "../storage/ExpoAttachmentFileStore";
import { productionIds } from "../storage/productionIdentity";
import { SQLiteFieldNotesRepository } from "../storage/SQLiteFieldNotesRepository";
import { StorageReconciler } from "../storage/StorageReconciler";

type StorageStatus = "opening" | "ready" | "error";

type RuntimeServices = {
  repository: SQLiteFieldNotesRepository;
  attachments: AppOwnedAttachmentService;
  reconciler: StorageReconciler;
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
  revision: number;
  appState: AppStateStatus;
  storageStatus: StorageStatus;
  storageError: string | null;
  reconciliation: StorageReconciliationReport | null;
};

const RuntimeContext = createContext<RuntimeValue | null>(null);

function createServices(): RuntimeServices {
  const repository = new SQLiteFieldNotesRepository();
  const files = new ExpoAttachmentFileStore();
  return {
    repository,
    attachments: new AppOwnedAttachmentService(repository, files),
    reconciler: new StorageReconciler(repository, files),
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

  const reconcileStorage = useCallback(async () => {
    await repository.ready();
    const report = await services.reconciler.reconcile();
    setReconciliation(report);
    setRevision((value) => value + 1);
    return report;
  }, [repository, services.reconciler]);

  useEffect(() => {
    let active = true;
    void repository
      .ready()
      .then(() => services.reconciler.reconcile())
      .then((report) => {
        if (!active) return;
        setReconciliation(report);
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
  }, [repository, services.reconciler]);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      setAppState(nextState);
      if (nextState === "active" && storageStatus === "ready") {
        void reconcileStorage().catch((error: unknown) => {
          setStorageError(`storage reconciliation failed: ${String(error)}`);
        });
      }
    });
    return () => subscription.remove();
  }, [reconcileStorage, storageStatus]);

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
      revision,
      appState,
      storageStatus,
      storageError,
      reconciliation,
    }),
    [
      appState,
      attachTestFile,
      deleteRecord,
      getRecord,
      inspectStorage,
      listAttachments,
      listOutbox,
      listRecords,
      newRecordId,
      reconcileStorage,
      reconciliation,
      repository,
      revision,
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
