import type { RecordPayload } from "@field-notes/shared";
import { useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { useAppRuntime } from "../../src/application/AppRuntime";
import {
  RecordForm,
  type RecordDraft,
} from "../../src/components/RecordForm";
import { Screen } from "../../src/components/Screen";
import { nextInMemoryRecordId } from "../../src/data/recordId";
import { useUnsavedDraftGuard } from "../../src/navigation/useUnsavedDraftGuard";

export default function NewRecordRoute() {
  const router = useRouter();
  const { saveRecord } = useAppRuntime();
  const [dirty, setDirty] = useState(false);
  const permitNavigation = useUnsavedDraftGuard(dirty);
  const initialValue = useMemo<RecordDraft>(
    () => ({ title: "", notes: "", status: "draft", observedAt: new Date().toISOString() }),
    [],
  );

  const save = async (draft: RecordDraft) => {
    const id = nextInMemoryRecordId();
    const payload: RecordPayload = { ...draft };
    await saveRecord({ id, expectedLocalRevision: null, payload });
    permitNavigation();
    router.replace(`/records/${id}`);
  };

  return (
    <Screen
      description="저장은 현재 process의 메모리만 바꿉니다. Stage 02에서 SQLite transaction으로 교체합니다."
      keyboardAware
      title="새 현장 기록"
    >
      <RecordForm
        initialValue={initialValue}
        onCancel={() => router.back()}
        onDirtyChange={setDirty}
        onSubmit={save}
      />
    </Screen>
  );
}

