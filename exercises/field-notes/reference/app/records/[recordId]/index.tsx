import type { FieldRecord } from "@field-notes/shared";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../../../src/application/AppRuntime";
import { ActionButton } from "../../../src/components/ActionButton";
import { Screen } from "../../../src/components/Screen";
import { StateNotice } from "../../../src/components/StateNotice";
import { normalizeRecordId } from "../../../src/navigation/stage01";

export default function RecordDetailRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ recordId?: string | string[] }>();
  const { getRecord, revision } = useAppRuntime();
  const [record, setRecord] = useState<FieldRecord | null | undefined>(undefined);
  const rawId = Array.isArray(params.recordId) ? params.recordId[0] ?? "" : params.recordId ?? "";
  const normalized = normalizeRecordId(rawId);

  useEffect(() => {
    if (normalized.kind === "invalid") {
      setRecord(null);
      return;
    }
    let active = true;
    void getRecord(normalized.recordId).then((value) => {
      if (active) setRecord(value);
    });
    return () => {
      active = false;
    };
  }, [getRecord, normalized.kind, normalized.kind === "valid" ? normalized.recordId : normalized.reason, revision]);

  if (normalized.kind === "invalid") {
    return (
      <Screen title="잘못된 기록 ID">
        <StateNotice
          kind="error"
          message={`route parameter가 계약을 만족하지 않습니다 (${normalized.reason}).`}
          title="기록 ID를 해석할 수 없습니다"
        />
        <ActionButton label="목록으로" onPress={() => router.replace("/records")} />
      </Screen>
    );
  }
  if (record === undefined) {
    return <Screen title="기록 불러오는 중" />;
  }
  if (record === null) {
    return (
      <Screen title="기록 없음">
        <StateNotice
          kind="error"
          message={`유효한 ID(${normalized.recordId})이지만 fixture repository에 대상이 없습니다.`}
          title="존재하지 않는 기록"
        />
        <ActionButton label="목록으로" onPress={() => router.replace("/records")} />
      </Screen>
    );
  }

  return (
    <Screen
      headerAction={
        <ActionButton
          label="편집"
          onPress={() => router.push(`/records/${encodeURIComponent(record.id)}/edit`)}
        />
      }
      title={record.title}
    >
      <View style={styles.card}>
        <Text style={styles.label}>메모</Text>
        <Text selectable style={styles.value}>{record.notes || "메모 없음"}</Text>
        <Text style={styles.label}>상태</Text>
        <Text style={styles.value}>{record.status}</Text>
        <Text style={styles.label}>관찰 시각</Text>
        <Text style={styles.value}>{record.observedAt}</Text>
        <Text style={styles.label}>동기화</Text>
        <Text style={styles.value}>{record.syncState} · local revision {record.localRevision}</Text>
      </View>
      <StateNotice
        message="Stage 03에서 app-owned 사진과 선택적 위치를 연결합니다. 임시 picker URI를 영구 상태로 취급하지 않습니다."
        title="첨부 파일 placeholder"
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 16, backgroundColor: "#fffdf8", padding: 18, gap: 7 },
  label: { marginTop: 8, color: "#5c716b", fontSize: 13, fontWeight: "800" },
  value: { color: "#173b33", fontSize: 17, lineHeight: 25 },
});

