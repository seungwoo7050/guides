import type { RecordPayload } from "@field-notes/shared";
import { useRouter } from "expo-router";
import { useMemo, useState } from "react";
import { useAppRuntime } from "../../src/application/AppRuntime";
import {
  RecordForm,
  type RecordDraft,
} from "../../src/components/RecordForm";
import { Screen } from "../../src/components/Screen";
import { StateNotice } from "../../src/components/StateNotice";
import { useUnsavedDraftGuard } from "../../src/navigation/useUnsavedDraftGuard";

export default function NewRecordRoute() {
  const router = useRouter();
  const { newRecordId, saveRecord } = useAppRuntime();
  const [dirty, setDirty] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const permitNavigation = useUnsavedDraftGuard(dirty);
  const initialValue = useMemo<RecordDraft>(
    () => ({ title: "", notes: "", status: "draft", observedAt: new Date().toISOString() }),
    [],
  );
  const recordId = useMemo(() => newRecordId(), [newRecordId]);

  const save = async (draft: RecordDraft) => {
    const payload: RecordPayload = { ...draft };
    try {
      await saveRecord({ id: recordId, expectedLocalRevision: null, payload });
      setSaveError(null);
      permitNavigation();
      router.replace(`/records/${encodeURIComponent(recordId)}`);
    } catch (error) {
      setSaveError(String(error));
    }
  };

  return (
    <Screen
      description="저장은 record revision과 immutable outbox snapshot을 하나의 SQLite transaction으로 commit합니다."
      keyboardAware
      title="새 현장 기록"
    >
      {saveError ? (
        <StateNotice
          kind="error"
          message={`${saveError} 입력 내용은 화면에 남아 있으므로 원인을 확인한 뒤 다시 시도하세요.`}
          title="저장하지 못했습니다"
        />
      ) : null}
      <RecordForm
        initialValue={initialValue}
        onCancel={() => router.back()}
        onDirtyChange={setDirty}
        onSubmit={save}
      />
    </Screen>
  );
}
