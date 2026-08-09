import type { Attachment, FieldRecord } from "@field-notes/shared";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../../../src/application/AppRuntime";
import { ActionButton } from "../../../src/components/ActionButton";
import { Screen } from "../../../src/components/Screen";
import { StateNotice } from "../../../src/components/StateNotice";
import { normalizeRecordId } from "../../../src/navigation/stage01";

export default function RecordDetailRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ recordId?: string | string[] }>();
  const {
    attachTestFile,
    deleteRecord,
    getRecord,
    listAttachments,
    revision,
  } = useAppRuntime();
  const [record, setRecord] = useState<FieldRecord | null | undefined>(undefined);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const rawId = Array.isArray(params.recordId) ? params.recordId[0] ?? "" : params.recordId ?? "";
  const normalized = normalizeRecordId(rawId);

  useEffect(() => {
    if (normalized.kind === "invalid") {
      setRecord(null);
      return;
    }
    let active = true;
    void Promise.all([
      getRecord(normalized.recordId),
      listAttachments(normalized.recordId),
    ])
      .then(([value, attachmentRows]) => {
        if (!active) return;
        setRecord(value);
        setAttachments(attachmentRows);
        setOperationError(null);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setRecord(null);
        setOperationError(String(error));
      });
    return () => {
      active = false;
    };
  }, [getRecord, listAttachments, normalized.kind, normalized.kind === "valid" ? normalized.recordId : normalized.reason, revision]);

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
          message={operationError ?? `유효한 ID(${normalized.recordId})이지만 SQLite에 활성 기록이 없습니다.`}
          title="존재하지 않는 기록"
        />
        <ActionButton label="목록으로" onPress={() => router.replace("/records")} />
      </Screen>
    );
  }

  const addTestAttachment = async () => {
    setWorking(true);
    try {
      await attachTestFile(record.id);
      setOperationError(null);
    } catch (error) {
      setOperationError(String(error));
    } finally {
      setWorking(false);
    }
  };

  const confirmDelete = () => {
    Alert.alert(
      "기록을 삭제할까요?",
      "행을 즉시 지우지 않고 tombstone과 delete command를 같은 transaction에 남깁니다.",
      [
        { text: "취소", style: "cancel" },
        {
          text: "삭제",
          style: "destructive",
          onPress: () => {
            setWorking(true);
            void deleteRecord(record.id, record.localRevision)
              .then(() => {
                setOperationError(null);
                router.replace("/records");
              })
              .catch((error: unknown) => setOperationError(String(error)))
              .finally(() => setWorking(false));
          },
        },
      ],
    );
  };

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
      {operationError ? (
        <StateNotice kind="error" message={operationError} title="로컬 작업을 완료하지 못했습니다" />
      ) : null}
      <View style={styles.card}>
        <Text style={styles.label}>app-owned 첨부 파일</Text>
        {attachments.filter((attachment) => attachment.state !== "removed").length === 0 ? (
          <Text style={styles.value}>첨부 없음</Text>
        ) : (
          attachments
            .filter((attachment) => attachment.state !== "removed")
            .map((attachment) => (
              <View key={attachment.id} style={styles.attachment}>
                <Text selectable style={styles.attachmentId}>{attachment.id}</Text>
                <Text
                  accessibilityRole={attachment.state === "missing-local-file" ? "alert" : undefined}
                  style={attachment.state === "missing-local-file" ? styles.missing : styles.value}
                >
                  {attachment.state} · {attachment.byteSize} bytes
                </Text>
              </View>
            ))
        )}
      </View>
      <StateNotice
        message="아래 버튼은 permission 없이 작은 비민감 fixture를 cache→staging→app-owned 경로로 복사합니다. 실제 camera/photo picker와 위치는 Stage 03의 명시적 비소유 범위입니다."
        title="파일 소유권 증명 경로"
      />
      <View style={styles.actions}>
        <ActionButton
          disabled={working}
          label={working ? "처리 중…" : "test file 추가"}
          onPress={() => void addTestAttachment()}
          variant="secondary"
        />
        <ActionButton
          disabled={working}
          label="기록 삭제"
          onPress={confirmDelete}
          variant="danger"
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 16, backgroundColor: "#fffdf8", padding: 18, gap: 7 },
  label: { marginTop: 8, color: "#5c716b", fontSize: 13, fontWeight: "800" },
  value: { color: "#173b33", fontSize: 17, lineHeight: 25 },
  attachment: { borderTopWidth: 1, borderTopColor: "#d8ded9", paddingTop: 10, gap: 4 },
  attachmentId: { color: "#4e625d", fontSize: 13 },
  missing: { color: "#9f3327", fontSize: 16, fontWeight: "800" },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
});
