import type { FieldRecord } from "@field-notes/shared";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, View } from "react-native";
import { useAppRuntime } from "../../src/application/AppRuntime";
import { ActionButton } from "../../src/components/ActionButton";
import { RecordListItem } from "../../src/components/RecordListItem";
import { Screen } from "../../src/components/Screen";
import { StateNotice } from "../../src/components/StateNotice";

function startupMessage(value: string | string[] | undefined): string | null {
  const notice = Array.isArray(value) ? value[0] : value;
  if (notice?.startsWith("missing:")) {
    return `요청한 기록(${notice.slice("missing:".length)})이 현재 저장소에 없습니다.`;
  }
  if (notice?.startsWith("invalid:")) {
    return `안전하지 않거나 해석할 수 없는 링크를 기록 목록으로 보냈습니다 (${notice.slice("invalid:".length)}).`;
  }
  return null;
}

export default function RecordsRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ startupNotice?: string | string[] }>();
  const { listRecords, revision } = useAppRuntime();
  const [records, setRecords] = useState<FieldRecord[]>([]);

  useEffect(() => {
    let active = true;
    void listRecords().then((value) => {
      if (active) setRecords(value);
    });
    return () => {
      active = false;
    };
  }, [listRecords, revision]);

  const message = startupMessage(params.startupNotice);
  return (
    <Screen
      description="Stage 01은 세 개의 fixture를 메모리에만 보관합니다. 앱 process가 끝나면 편집 결과는 사라집니다."
      headerAction={<ActionButton label="새 기록" onPress={() => router.push("/records/new")} />}
      title="현장 기록"
    >
      {message ? (
        <StateNotice kind="error" message={message} title="안전한 시작 경로로 복구했습니다" />
      ) : null}
      <View style={styles.navigation}>
        <ActionButton label="동기화 상태" onPress={() => router.push("/sync")} variant="secondary" />
        <ActionButton label="설정" onPress={() => router.push("/settings")} variant="secondary" />
      </View>
      <View accessibilityLabel="기록 목록" style={styles.list}>
        {records.map((record) => (
          <RecordListItem
            key={record.id}
            onPress={() => router.push(`/records/${encodeURIComponent(record.id)}`)}
            record={record}
          />
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  navigation: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  list: { gap: 12 },
});

