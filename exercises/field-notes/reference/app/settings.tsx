import type { LocalDatabaseSnapshot } from "@field-notes/shared";
import Constants from "expo-constants";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../src/application/AppRuntime";
import { Screen } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

export default function SettingsRoute() {
  const {
    appState,
    capabilities,
    inspectStorage,
    reconciliation,
    revision,
    storageError,
    storageStatus,
    syncEndpoint,
  } = useAppRuntime();
  const [snapshot, setSnapshot] = useState<LocalDatabaseSnapshot | null>(null);

  useEffect(() => {
    let active = true;
    void inspectStorage()
      .then((value) => {
        if (active) setSnapshot(value);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [inspectStorage, revision]);

  return (
    <Screen title="설정">
      <View style={styles.card}>
        <Text style={styles.label}>앱 버전</Text>
        <Text style={styles.value}>{Constants.expoConfig?.version ?? "unknown"}</Text>
        <Text style={styles.label}>runtime</Text>
        <Text style={styles.value}>Expo SDK 57 · React Native 0.86</Text>
        <Text style={styles.label}>저장소</Text>
        <Text style={styles.value}>SQLite schema v{snapshot?.schemaVersion ?? "…"} · {storageStatus}</Text>
        <Text style={styles.label}>durable outbox</Text>
        <Text style={styles.value}>{snapshot?.outbox.length ?? "…"} commands</Text>
        <Text style={styles.label}>수동 sync endpoint</Text>
        <Text selectable style={styles.value}>{syncEndpoint}</Text>
        <Text style={styles.label}>관찰한 app lifecycle</Text>
        <Text style={styles.value}>{appState}</Text>
        <Text style={styles.label}>camera access</Text>
        <Text style={styles.value}>
          {capabilities === null ? "checking" : `${capabilities.camera.availability.kind} · ${capabilities.camera.permission.kind}`}
        </Text>
        <Text style={styles.label}>system picker access</Text>
        <Text style={styles.value}>
          {capabilities === null ? "checking" : `${capabilities.photoPicker.availability.kind} · ${capabilities.photoPicker.permission.kind}`}
        </Text>
        <Text style={styles.label}>foreground location access</Text>
        <Text style={styles.value}>
          {capabilities === null ? "checking" : `${capabilities.location.availability.kind} · ${capabilities.location.permission.kind}`}
        </Text>
      </View>
      {storageError ? (
        <StateNotice kind="error" message={storageError} title="저장소 진단" />
      ) : null}
      <StateNotice
        message={
          reconciliation === null
            ? "startup reconciliation 결과를 기다리고 있습니다."
            : `staging ${reconciliation.stagingFilesRemoved}개, orphan ${reconciliation.removedOrphanUris.length}개, missing ${reconciliation.missingAttachmentIds.length}개, cleanup ${reconciliation.removedAttachmentIds.length}개, failure ${reconciliation.failures.length}개`
        }
        title="마지막 파일 정합성 검사"
      />
      <StateNotice
        message="Camera, system picker, foreground one-shot location과 remote sync는 사용자 action에서만 실행합니다. app active 복귀는 capability/pending media만 다시 읽고 network·민감 action을 자동 실행하지 않습니다. Fetch transport는 configurable local/test endpoint뿐이며 background sync, background location과 production backend는 후속 범위입니다."
        title="기능 경계"
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { padding: 18, borderRadius: 16, backgroundColor: "#fffdf8", gap: 6 },
  label: { marginTop: 8, fontSize: 13, fontWeight: "800", color: "#5c716b" },
  value: { fontSize: 17, color: "#173b33" },
});
