import type {
  FieldRecord,
  RecordPayload,
  Stage01RecordRepository,
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
import { InMemoryRecordRepository } from "../data/InMemoryRecordRepository";

type RuntimeValue = {
  repository: Stage01RecordRepository;
  listRecords(): Promise<FieldRecord[]>;
  getRecord(id: string): Promise<FieldRecord | null>;
  saveRecord(input: {
    id: string;
    expectedLocalRevision: number | null;
    payload: RecordPayload;
  }): Promise<FieldRecord>;
  revision: number;
  appState: AppStateStatus;
};

const RuntimeContext = createContext<RuntimeValue | null>(null);

export function AppRuntimeProvider({ children }: PropsWithChildren) {
  const repository = useRef(new InMemoryRecordRepository()).current;
  const [revision, setRevision] = useState(0);
  const [appState, setAppState] = useState<AppStateStatus>(AppState.currentState);

  useEffect(() => {
    const subscription = AppState.addEventListener("change", setAppState);
    return () => subscription.remove();
  }, []);

  const listRecords = useCallback(() => repository.list(), [repository]);
  const getRecord = useCallback((id: string) => repository.get(id), [repository]);
  const saveRecord = useCallback(
    async (input: {
      id: string;
      expectedLocalRevision: number | null;
      payload: RecordPayload;
    }) => {
      const record = await repository.saveInMemory(input);
      setRevision((value) => value + 1);
      return record;
    },
    [repository],
  );

  const value = useMemo<RuntimeValue>(
    () => ({
      repository,
      listRecords,
      getRecord,
      saveRecord,
      revision,
      appState,
    }),
    [appState, getRecord, listRecords, repository, revision, saveRecord],
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
