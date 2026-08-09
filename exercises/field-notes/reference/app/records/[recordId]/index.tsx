import type {
  Attachment,
  CapabilityAvailability,
  FieldRecord,
  PermissionState,
  RecordPayload,
} from "@field-notes/shared";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { Alert, StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../../../src/application/AppRuntime";
import { ActionButton } from "../../../src/components/ActionButton";
import { Screen } from "../../../src/components/Screen";
import { StateNotice } from "../../../src/components/StateNotice";
import { normalizeRecordId } from "../../../src/navigation/stage01";
import type { MediaActionOutcome } from "../../../src/device/DeviceFeatureCoordinator";

function availabilityLabel(value: CapabilityAvailability | undefined): string {
  if (value === undefined) return "checking";
  if (value.kind === "available") return "available";
  return `${value.kind}: ${value.kind === "limited" ? value.description : value.reason}`;
}

function permissionLabel(value: PermissionState | undefined): string {
  if (value === undefined) return "checking";
  if (value.kind === "limited") return `limited: ${value.description}`;
  if (value.kind === "restricted") return `restricted: ${value.reason}`;
  if (value.kind === "denied") {
    return `denied · canAskAgain=${String(value.canAskAgain)}`;
  }
  return value.kind;
}

function mediaOutcomeMessage(outcome: MediaActionOutcome | null): string | null {
  if (outcome === null || outcome.kind === "none") return null;
  if (outcome.kind === "attached") {
    return outcome.recovered
      ? "process recreation 뒤 pending result를 복구해 사진을 한 번 연결했습니다."
      : "temporary result를 app-owned file로 전환해 사진을 연결했습니다.";
  }
  if (outcome.kind === "cancelled") return "사용자가 system UI를 취소했습니다. 기록은 바뀌지 않았습니다.";
  if (outcome.kind === "denied") {
    return outcome.permission.kind === "denied" && !outcome.permission.canAskAgain
      ? "권한을 다시 요청할 수 없습니다. OS Settings에서 변경하거나 다른 source를 사용하세요."
      : "권한을 허용하지 않았습니다. 다른 source 또는 text-only 기록을 계속 사용할 수 있습니다.";
  }
  if (outcome.kind === "unavailable") return `기능을 사용할 수 없습니다: ${outcome.reason}`;
  if (outcome.kind === "failed") return `사진을 연결하지 못했습니다: ${outcome.reason}`;
  if (outcome.kind === "interrupted") return outcome.reason;
  if (outcome.kind === "duplicate") return "이미 조정한 external result라 중복 attachment를 만들지 않았습니다.";
  return "다른 external media 작업이 진행 중입니다.";
}

function payloadWithLocation(
  record: FieldRecord,
  location: RecordPayload["location"],
): RecordPayload {
  return {
    title: record.title,
    notes: record.notes,
    status: record.status,
    observedAt: record.observedAt,
    location,
  };
}

export default function RecordDetailRoute() {
  const router = useRouter();
  const params = useLocalSearchParams<{ recordId?: string | string[] }>();
  const {
    attachTestFile,
    capabilities,
    capturePhoto,
    deleteRecord,
    getRecord,
    listAttachments,
    lastMediaOutcome,
    measureLocation,
    pickPhoto,
    revision,
    saveRecord,
  } = useAppRuntime();
  const [record, setRecord] = useState<FieldRecord | null | undefined>(undefined);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [mediaMessage, setMediaMessage] = useState<string | null>(null);
  const [locationMessage, setLocationMessage] = useState<string | null>(null);
  const [locationPreview, setLocationPreview] =
    useState<NonNullable<RecordPayload["location"]> | null>(null);
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

  const acquirePhoto = async (source: "camera" | "photo-picker") => {
    setWorking(true);
    try {
      const outcome =
        source === "camera" ? await capturePhoto(record.id) : await pickPhoto(record.id);
      setMediaMessage(mediaOutcomeMessage(outcome));
      setOperationError(null);
    } catch {
      setOperationError("사진 action을 완료하지 못했습니다. 기존 기록은 보존됩니다.");
    } finally {
      setWorking(false);
    }
  };

  const previewCurrentLocation = async () => {
    setWorking(true);
    try {
      const outcome = await measureLocation();
      if (outcome.kind === "preview") {
        setLocationPreview(outcome.location);
        setLocationMessage(
          "측정값은 아직 memory preview입니다. 아래 포함 버튼을 눌러야 SQLite/outbox에 저장됩니다.",
        );
      } else if (outcome.kind === "denied") {
        setLocationMessage("foreground 위치 권한을 허용하지 않았습니다. 위치 없이 기록을 계속 사용할 수 있습니다.");
      } else if (outcome.kind === "interrupted") {
        setLocationMessage("app lifecycle 변화로 늦은 위치 결과를 버렸습니다. 자동으로 다시 측정하지 않습니다.");
      } else {
        setLocationMessage(`위치를 측정하지 못했습니다: ${outcome.reason}`);
      }
    } finally {
      setWorking(false);
    }
  };

  const saveLocation = async (
    location: RecordPayload["location"],
    successMessage: string,
  ) => {
    setWorking(true);
    try {
      await saveRecord({
        id: record.id,
        expectedLocalRevision: record.localRevision,
        payload: payloadWithLocation(record, location),
      });
      setLocationPreview(null);
      setLocationMessage(successMessage);
      setOperationError(null);
    } catch {
      setOperationError("위치 변경을 저장하지 못했습니다. preview와 기존 record는 보존됩니다.");
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
        <Text style={styles.label}>사용자가 포함한 위치</Text>
        <Text selectable style={styles.value}>
          {record.location === undefined
            ? "없음 (정상적인 선택)"
            : `${record.location.latitude.toFixed(6)}, ${record.location.longitude.toFixed(6)} · ±${record.location.accuracyMeters.toFixed(1)}m · ${record.location.measuredAt}`}
        </Text>
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
        message="system picker는 보관함 전체 permission을 요청하지 않고 사용자가 고른 한 장만 받습니다. Camera permission은 촬영 버튼 문맥에서만 요청합니다. 취소·거절·실패는 text record를 바꾸지 않습니다."
        title="사진 source와 최소 권한"
      />
      <View style={styles.card}>
        <Text style={styles.label}>Camera</Text>
        <Text style={styles.value}>{availabilityLabel(capabilities?.camera.availability)}</Text>
        <Text style={styles.value}>{permissionLabel(capabilities?.camera.permission)}</Text>
        <Text style={styles.label}>System photo picker</Text>
        <Text style={styles.value}>{availabilityLabel(capabilities?.photoPicker.availability)}</Text>
        <Text style={styles.value}>{permissionLabel(capabilities?.photoPicker.permission)}</Text>
      </View>
      <View style={styles.actions}>
        <ActionButton
          disabled={working}
          label={working ? "처리 중…" : "System picker에서 선택"}
          onPress={() => void acquirePhoto("photo-picker")}
        />
        <ActionButton
          disabled={working}
          label="Camera로 촬영"
          onPress={() => void acquirePhoto("camera")}
          variant="secondary"
        />
        <ActionButton
          disabled={working}
          label="Stage 02 test file"
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
      {mediaMessage ?? mediaOutcomeMessage(lastMediaOutcome) ? (
        <StateNotice
          message={mediaMessage ?? mediaOutcomeMessage(lastMediaOutcome) ?? ""}
          title="마지막 사진 action"
        />
      ) : null}
      <StateNotice
        message="foreground one-shot 측정은 아래 사용자 action에서만 시작합니다. 위치 첨부는 선택이며 startup prompt, last-known fallback, background tracking은 없습니다."
        title="선택적 위치"
      />
      <View style={styles.card}>
        <Text style={styles.label}>Foreground location</Text>
        <Text style={styles.value}>{availabilityLabel(capabilities?.location.availability)}</Text>
        <Text style={styles.value}>{permissionLabel(capabilities?.location.permission)}</Text>
        {locationPreview ? (
          <View style={styles.attachment}>
            <Text style={styles.label}>memory-only preview</Text>
            <Text selectable style={styles.value}>
              {locationPreview.latitude.toFixed(6)}, {locationPreview.longitude.toFixed(6)} · ±{locationPreview.accuracyMeters.toFixed(1)}m · {locationPreview.measuredAt}
            </Text>
          </View>
        ) : null}
      </View>
      <View style={styles.actions}>
        <ActionButton
          disabled={working}
          label="현재 위치 측정"
          onPress={() => void previewCurrentLocation()}
          variant="secondary"
        />
        <ActionButton
          disabled={working || locationPreview === null}
          label="Preview를 record에 포함"
          onPress={() => void saveLocation(locationPreview ?? undefined, "선택한 위치를 record와 최신 pending outbox에 저장했습니다.")}
        />
        <ActionButton
          disabled={working || record.location === undefined}
          label="저장된 위치 제거"
          onPress={() => void saveLocation(undefined, "record와 아직 미시도 pending command에서 위치를 제거했습니다.")}
          variant="danger"
        />
      </View>
      {locationMessage ? (
        <StateNotice message={locationMessage} title="위치 action 결과" />
      ) : null}
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
