import type { LocalDatabaseSnapshot } from "@field-notes/shared";
import Constants from "expo-constants";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../src/application/AppRuntime";
import { ActionButton } from "../src/components/ActionButton";
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
    backgroundRegistration,
    registerBackgroundOpportunity,
    unregisterBackgroundOpportunity,
    notificationRegistration,
    pendingNotificationAction,
    registerNotifications,
    retryPendingNotification,
  } = useAppRuntime();
  const [snapshot, setSnapshot] = useState<LocalDatabaseSnapshot | null>(null);
  const [lifecycleAction, setLifecycleAction] = useState<string | null>(null);

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
        <Text style={styles.label}>background task</Text>
        <Text style={styles.value}>
          {backgroundRegistration === null
            ? "checking"
            : `${backgroundRegistration.availability} · ${backgroundRegistration.registered ? "registered" : "not registered"}`}
        </Text>
        <Text style={styles.label}>notification registration</Text>
        <Text style={styles.value}>
          {notificationRegistration.kind}
          {notificationRegistration.kind === "permission-denied"
            ? ` · canAskAgain=${notificationRegistration.canAskAgain}`
            : "reason" in notificationRegistration
              ? ` · ${notificationRegistration.reason}`
              : notificationRegistration.kind === "token-ready"
                ? ` · ${notificationRegistration.permission}`
                : ""}
        </Text>
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
      <View style={styles.actions}>
        <ActionButton
          label="Android 알림 명시적으로 준비"
          onPress={() => {
            setLifecycleAction(null);
            void registerNotifications()
              .then((result) => setLifecycleAction(`notification: ${result.kind}`))
              .catch(() => setLifecycleAction("notification: safe failure"));
          }}
        />
        <ActionButton
          label="background 실행 기회만 등록 (sync 비활성)"
          onPress={() => {
            setLifecycleAction(null);
            void registerBackgroundOpportunity()
              .then((result) => setLifecycleAction(
                `background: ${result.registered ? "registered" : result.availability}`,
              ))
              .catch(() => setLifecycleAction("background: safe failure"));
          }}
          variant="secondary"
        />
        <ActionButton
          label="background 실행 기회 등록 해제"
          onPress={() => {
            setLifecycleAction(null);
            void unregisterBackgroundOpportunity()
              .then(() => setLifecycleAction("background: unregistered"))
              .catch(() => setLifecycleAction("background cleanup: safe failure"));
          }}
          variant="secondary"
        />
        {pendingNotificationAction ? (
          <ActionButton
            label="보류한 알림 경로 다시 적용"
            onPress={() => {
              void retryPendingNotification().catch(() => {
                setLifecycleAction("notification retry: safe failure");
              });
            }}
            variant="secondary"
          />
        ) : null}
      </View>
      {lifecycleAction !== null ? (
        <StateNotice title="마지막 lifecycle action" message={lifecycleAction} />
      ) : null}
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
        message="Camera, picker, foreground location, notification permission/token, background registration은 startup에서 요청하지 않습니다. 등록은 OS 기회 관찰일 뿐 sync 완료 증거가 아닙니다. token·payload는 표시하거나 기록하지 않으며 installation/backend mapping은 구현하지 않았습니다."
        title="기능 경계"
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: { padding: 18, borderRadius: 16, backgroundColor: "#fffdf8", gap: 6 },
  label: { marginTop: 8, fontSize: 13, fontWeight: "800", color: "#5c716b" },
  value: { fontSize: 17, color: "#173b33" },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
});
