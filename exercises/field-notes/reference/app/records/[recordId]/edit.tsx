import type { FieldRecord, RecordPayload } from "@field-notes/shared";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { useAppRuntime } from "../../../src/application/AppRuntime";
import { ActionButton } from "../../../src/components/ActionButton";
import { RecordForm, type RecordDraft } from "../../../src/components/RecordForm";
import { Screen } from "../../../src/components/Screen";
import { StateNotice } from "../../../src/components/StateNotice";
import { normalizeRecordId } from "../../../src/navigation/stage01";
import { useUnsavedDraftGuard } from "../../../src/navigation/useUnsavedDraftGuard";

export default function EditRecordRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ recordId?: string | string[] }>();
  const { getRecord, saveRecord } = useAppRuntime();
  const [record, setRecord] = useState<FieldRecord | null | undefined>(undefined);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  const permitNavigation = useUnsavedDraftGuard(dirty);
  const rawId = Array.isArray(params.recordId) ? params.recordId[0] ?? "" : params.recordId ?? "";
  const normalized = normalizeRecordId(rawId);

  useEffect(() => {
    if (normalized.kind === "invalid") {
      setRecord(null);
      return;
    }
    let active = true;
    void getRecord(normalized.recordId)
      .then((value) => {
        if (!active) return;
        setRecord(value);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setRecord(null);
        setLoadError(String(error));
      });
    return () => {
      active = false;
    };
  }, [getRecord, normalized.kind, normalized.kind === "valid" ? normalized.recordId : normalized.reason]);

  if (normalized.kind === "invalid" || record === null) {
    return (
      <Screen title="편집할 수 없음">
        <StateNotice
          kind="error"
          message={normalized.kind === "invalid" ? `잘못된 ID: ${normalized.reason}` : loadError ?? "유효한 ID지만 대상 기록이 없습니다."}
          title="편집 대상을 확인하세요"
        />
        <ActionButton label="목록으로" onPress={() => router.replace("/records")} />
      </Screen>
    );
  }
  if (record === undefined) {
    return <Screen title="기록 불러오는 중" />;
  }

  const initialValue: RecordDraft = {
    title: record.title,
    notes: record.notes,
    status: record.status,
    observedAt: record.observedAt,
  };
  const save = async (draft: RecordDraft) => {
    const payload: RecordPayload = { ...draft, location: record.location };
    try {
      await saveRecord({
        id: record.id,
        expectedLocalRevision: record.localRevision,
        payload,
      });
      setSaveError(null);
      permitNavigation();
      router.replace(`/records/${encodeURIComponent(record.id)}`);
    } catch (error) {
      setSaveError(String(error));
    }
  };

  return (
    <Screen
      description="긴 제목 오류가 나도 draft와 현재 화면은 유지됩니다."
      keyboardAware
      title="기록 편집"
    >
      {saveError ? (
        <StateNotice
          kind="error"
          message={`${saveError} 다른 write가 revision을 바꿨다면 최신 기록을 다시 연 뒤 적용할 내용을 판단하세요.`}
          title="변경을 commit하지 못했습니다"
        />
      ) : null}
      <RecordForm
        initialValue={initialValue}
        onCancel={() => router.back()}
        onDirtyChange={setDirty}
        onSubmit={save}
        submitLabel="변경 저장"
      />
    </Screen>
  );
}
