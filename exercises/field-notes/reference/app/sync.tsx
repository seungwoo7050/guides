import type { OutboxEntry } from "@field-notes/shared";
import { useRouter } from "expo-router";
import { useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../src/application/AppRuntime";
import { ActionButton } from "../src/components/ActionButton";
import { Screen } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

export default function SyncRoute() {
  const router = useRouter();
  const { listOutbox, revision } = useAppRuntime();
  const [entries, setEntries] = useState<OutboxEntry[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void listOutbox()
      .then((value) => {
        if (!active) return;
        setEntries(value);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (active) setLoadError(String(error));
      });
    return () => {
      active = false;
    };
  }, [listOutbox, revision]);

  return (
    <Screen
      description={`${entries.filter((entry) => entry.state === "pending").length}개 command가 durable pending 상태입니다.`}
      title="동기화 상태"
    >
      <StateNotice
        message="Stage 02는 stable payload snapshot을 SQLite outbox에 쌓기만 합니다. transport 실행, retry, auth, conflict resolution은 Stage 04 전까지 시작하지 않습니다."
        title="의도적인 실행 경계"
      />
      {loadError ? (
        <StateNotice kind="error" message={loadError} title="outbox를 읽지 못했습니다" />
      ) : null}
      <View accessibilityLabel="로컬 outbox" style={styles.list}>
        {entries.length === 0 ? <Text style={styles.empty}>아직 생성된 command가 없습니다.</Text> : null}
        {entries.map((entry) => (
          <View key={entry.commandId} style={styles.card}>
            <Text style={styles.title}>{entry.operation} · {entry.state}</Text>
            <Text selectable style={styles.value}>{entry.recordId} · revision {entry.localRevision}</Text>
            <Text selectable style={styles.command}>{entry.commandId}</Text>
          </View>
        ))}
      </View>
      <ActionButton label="기록 목록" onPress={() => router.push("/records")} variant="secondary" />
    </Screen>
  );
}

const styles = StyleSheet.create({
  list: { gap: 10 },
  card: { borderRadius: 14, backgroundColor: "#fffdf8", padding: 16, gap: 5 },
  title: { color: "#173b33", fontSize: 16, fontWeight: "800" },
  value: { color: "#36564e", fontSize: 14 },
  command: { color: "#667b75", fontSize: 12 },
  empty: { color: "#4e625d", fontSize: 16 },
});
