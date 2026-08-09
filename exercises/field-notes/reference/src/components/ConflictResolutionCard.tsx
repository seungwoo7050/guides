import type {
  DurableConflict,
  RecordPayload,
} from "@field-notes/sync-engine";
import { useMemo, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { ActionButton } from "./ActionButton";
import { RecordForm, type RecordDraft } from "./RecordForm";

function payloadEvidence(payload: RecordPayload | null): string {
  if (payload === null) return "삭제됨";
  const location = payload.location === undefined
    ? "없음"
    : `${payload.location.latitude}, ${payload.location.longitude} ±${payload.location.accuracyMeters}m @ ${payload.location.measuredAt}`;
  return [
    `title: ${payload.title}`,
    `notes: ${payload.notes}`,
    `status: ${payload.status}`,
    `observedAt: ${payload.observedAt}`,
    `location: ${location}`,
  ].join("\n");
}

export function ConflictResolutionCard({
  conflict,
  disabled = false,
  onResolve,
}: {
  conflict: DurableConflict;
  disabled?: boolean;
  onResolve(
    choice: "remote" | "local" | "merge",
    payload?: RecordPayload,
  ): Promise<void> | void;
}) {
  const local = conflict.local.payload;
  const remote = conflict.remote?.payload ?? null;
  const attempted = conflict.attempted.payload;
  const initial = useMemo<RecordDraft>(() => {
    const source = local ?? remote ?? attempted;
    return source === null
      ? { title: "", notes: "", status: "draft", observedAt: new Date(0).toISOString() }
      : {
          title: source.title,
          notes: source.notes,
          status: source.status,
          observedAt: source.observedAt,
        };
  }, [attempted, local, remote]);
  const [locationSource, setLocationSource] = useState<"local" | "remote" | "none">(
    local?.location !== undefined ? "local" : remote?.location !== undefined ? "remote" : "none",
  );

  const merge = async (draft: RecordDraft) => {
    const location = locationSource === "local"
      ? local?.location
      : locationSource === "remote"
        ? remote?.location
        : undefined;
    await onResolve("merge", { ...draft, location });
  };

  return (
    <View accessibilityLabel={`conflict ${conflict.recordId}`} style={styles.card}>
      <Text style={styles.title}>{conflict.recordId}</Text>
      <Text style={styles.heading}>attempted / base v{conflict.attempted.baseVersion ?? "없음"}</Text>
      <Text selectable style={styles.evidence}>{payloadEvidence(attempted)}</Text>
      <Text style={styles.heading}>current local · revision {conflict.local.localRevision}</Text>
      <Text selectable style={styles.evidence}>{payloadEvidence(local)}</Text>
      <Text style={styles.heading}>current remote · v{conflict.remote?.version ?? "없음"}</Text>
      <Text selectable style={styles.evidence}>{payloadEvidence(remote)}</Text>
      <Text style={styles.heading}>location 병합 선택</Text>
      <View accessibilityRole="radiogroup" style={styles.actions}>
        {(["local", "remote", "none"] as const).map((source) => (
          <ActionButton
            accessibilityLabel={`병합 위치: ${source}${locationSource === source ? ", 선택됨" : ""}`}
            accessibilityRole="radio"
            checked={locationSource === source}
            key={source}
            label={source}
            onPress={() => setLocationSource(source)}
            variant={locationSource === source ? "primary" : "secondary"}
          />
        ))}
      </View>
      <RecordForm
        initialValue={initial}
        onCancel={() => undefined}
        onSubmit={merge}
        submitLabel="필드 병합 command 생성"
      />
      <View style={styles.actions}>
        <ActionButton
          disabled={disabled}
          label="최신 local 다시 전송"
          onPress={() => void onResolve("local")}
        />
        <ActionButton
          disabled={disabled}
          label="remote 수용"
          onPress={() => void onResolve("remote")}
          variant="danger"
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#d8897e",
    backgroundColor: "#fff8f5",
    padding: 16,
    gap: 8,
  },
  title: { color: "#173b33", fontSize: 16, fontWeight: "800" },
  heading: { color: "#36564e", fontSize: 14, fontWeight: "800" },
  evidence: { color: "#36564e", fontSize: 13, lineHeight: 19 },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
});
