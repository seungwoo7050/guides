import type { RepositorySnapshot } from "@field-notes/sync-engine";
import { useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../src/application/AppRuntime";
import { ActionButton } from "../src/components/ActionButton";
import { Screen } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

function commandDetail(
  command: RepositorySnapshot["commands"][number],
): string {
  const state = command.state;
  if (state.kind === "in_flight") {
    return `attempt ${state.attempt} · lease ${state.lease.owner}`;
  }
  if (state.kind === "retry_wait") {
    return `attempt ${state.attempt} · retry ${new Date(state.nextAttemptAt).toLocaleTimeString()}`;
  }
  if (state.kind === "blocked_auth" || state.kind === "permanent") {
    return `attempt ${state.attempt} · ${state.reason}`;
  }
  if (state.kind === "conflict") {
    return `attempt ${state.attempt} · ${state.conflictId}`;
  }
  if (state.kind === "completed") {
    return `attempt ${state.attempt} · remote v${state.remoteVersion ?? "없음"}`;
  }
  return "아직 transport에 보내지 않음";
}

export default function SyncRoute() {
  const router = useRouter();
  const {
    inspectSync,
    lastSyncRun,
    resolveConflict,
    resumeBlockedAuth,
    revision,
    runManualSync,
    syncEndpoint,
    syncRunning,
  } = useAppRuntime();
  const [snapshot, setSnapshot] = useState<RepositorySnapshot | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [resolving, setResolving] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const value = await inspectSync();
    setSnapshot(value);
    return value;
  }, [inspectSync]);

  useEffect(() => {
    let active = true;
    void inspectSync()
      .then((value) => {
        if (active) setSnapshot(value);
      })
      .catch((error: unknown) => {
        if (active) setActionError(String(error));
      });
    return () => {
      active = false;
    };
  }, [inspectSync, revision]);

  const manualSync = () => {
    setActionError(null);
    void runManualSync()
      .then(() => reload())
      .catch((error: unknown) => setActionError(String(error)));
  };

  const resumeAuth = () => {
    setActionError(null);
    void resumeBlockedAuth()
      .then(() => reload())
      .catch((error: unknown) => setActionError(String(error)));
  };

  const resolve = (conflictId: string, choice: "remote" | "local") => {
    setResolving(conflictId);
    setActionError(null);
    void resolveConflict(conflictId, choice)
      .then(() => reload())
      .catch((error: unknown) => setActionError(String(error)))
      .finally(() => setResolving(null));
  };

  const unresolved = snapshot?.conflicts.filter(
    (conflict) => conflict.resolution === undefined,
  ) ?? [];
  const blockedCount = snapshot?.commands.filter(
    (command) => command.state.kind === "blocked_auth",
  ).length ?? 0;

  return (
    <Screen
      description="사용자가 누른 foreground action만 bounded worker를 실행합니다. 편집과 local commit은 network 결과와 독립적입니다."
      title="동기화 상태"
    >
      <StateNotice
        message={`test/local endpoint: ${syncEndpoint}. 이 앱은 운영 backend를 포함하거나 자동 시작하지 않습니다.`}
        title="명시적 transport 경계"
      />
      {lastSyncRun !== null ? (
        <StateNotice
          message={`${lastSyncRun.claimed}개 claim · ${lastSyncRun.checkpoints.length}개 checkpoint · ${lastSyncRun.stopped}`}
          title="마지막 수동 실행"
        />
      ) : null}
      {blockedCount > 0 ? (
        <StateNotice
          message="이 버튼은 로그인하거나 credential을 만들지 않습니다. 앱 밖의 허가된 session/auth 경로가 credential을 실제로 복구한 뒤에만 명시적으로 재개하세요."
          title="인증 복구가 먼저 필요합니다"
        />
      ) : null}
      {actionError !== null ? (
        <StateNotice
          kind="error"
          message={`${actionError}. local record 편집은 계속할 수 있습니다.`}
          title="동기화 action 실패"
        />
      ) : null}
      <View style={styles.actions}>
        <ActionButton
          disabled={syncRunning}
          label={syncRunning ? "동기화 중" : "지금 동기화"}
          onPress={manualSync}
        />
        <ActionButton
          disabled={blockedCount === 0 || syncRunning}
          label={`인증 준비 후 재개 (${blockedCount})`}
          onPress={resumeAuth}
          variant="secondary"
        />
      </View>

      <Text style={styles.section}>durable commands</Text>
      <View accessibilityLabel="durable sync commands" style={styles.list}>
        {snapshot?.commands.length === 0 ? (
          <Text style={styles.empty}>처리할 command가 없습니다.</Text>
        ) : null}
        {snapshot?.commands.map((entry) => (
          <View key={entry.command.commandId} style={styles.card}>
            <Text style={styles.title}>
              {entry.command.operation} · {entry.state.kind}
            </Text>
            <Text selectable style={styles.value}>
              {entry.command.recordId} · revision {entry.command.localRevision}
            </Text>
            <Text style={styles.value}>{commandDetail(entry)}</Text>
            <Text selectable style={styles.command}>{entry.command.commandId}</Text>
          </View>
        ))}
      </View>

      <Text style={styles.section}>해결하지 않은 충돌 ({unresolved.length})</Text>
      {unresolved.map((conflict) => (
        <View key={conflict.conflictId} style={styles.conflictCard}>
          <Text style={styles.title}>{conflict.recordId}</Text>
          <Text style={styles.value}>
            local revision {conflict.local.localRevision} · remote v{conflict.remote?.version ?? "없음"}
          </Text>
          <Text style={styles.value}>
            local: {conflict.local.payload?.title ?? "삭제"}
          </Text>
          <Text style={styles.value}>
            remote: {conflict.remote?.payload?.title ?? "삭제 또는 없음"}
          </Text>
          <StateNotice
            message="충돌 뒤 만든 최신 local edit도 허용됩니다. ‘local 다시 전송’은 현재 최신 local payload를 새 command ID로 만들고, ‘remote 수용’은 미시도 local command를 명시적으로 폐기합니다."
            title="해결 선택의 영향"
          />
          <View style={styles.actions}>
            <ActionButton
              disabled={resolving !== null}
              label="최신 local 다시 전송"
              onPress={() => resolve(conflict.conflictId, "local")}
            />
            <ActionButton
              disabled={resolving !== null}
              label="remote 수용"
              onPress={() => resolve(conflict.conflictId, "remote")}
              variant="danger"
            />
          </View>
        </View>
      ))}
      <ActionButton
        label="기록 목록"
        onPress={() => router.push("/records")}
        variant="secondary"
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  list: { gap: 10 },
  card: { borderRadius: 14, backgroundColor: "#fffdf8", padding: 16, gap: 5 },
  conflictCard: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#d8897e",
    backgroundColor: "#fff8f5",
    padding: 16,
    gap: 8,
  },
  section: { marginTop: 6, color: "#173b33", fontSize: 18, fontWeight: "800" },
  title: { color: "#173b33", fontSize: 16, fontWeight: "800" },
  value: { color: "#36564e", fontSize: 14 },
  command: { color: "#667b75", fontSize: 12 },
  empty: { color: "#4e625d", fontSize: 16 },
});
