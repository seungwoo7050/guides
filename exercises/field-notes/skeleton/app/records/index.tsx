import { FIELD_RECORD_FIXTURES } from "@field-notes/shared";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { Page } from "../../src/components/Page";
import { TodoNotice } from "../../src/components/TodoNotice";

export default function RecordsRoute() {
  const router = useRouter();
  return (
    <Page title="현장 기록">
      <TodoNotice title="Stage 01 시작 상태">
        startup intent, target 확인, duplicate 억제, process restoration이 아직 연결되지 않았습니다.
      </TodoNotice>
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" onPress={() => router.push("/records/new")} style={styles.button}><Text>새 기록</Text></Pressable>
        <Pressable accessibilityRole="button" onPress={() => router.push("/settings")} style={styles.button}><Text>설정</Text></Pressable>
      </View>
      {FIELD_RECORD_FIXTURES.map((record) => (
        <Pressable
          accessibilityLabel={`${record.title} 상세 열기`}
          accessibilityRole="button"
          key={record.id}
          onPress={() => router.push(`/records/${record.id}`)}
          style={styles.card}
        >
          <Text style={styles.title}>{record.title}</Text>
          <Text>{record.status} · {record.syncState}</Text>
        </Pressable>
      ))}
    </Page>
  );
}

const styles = StyleSheet.create({
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  button: { minHeight: 48, padding: 14, borderRadius: 10, backgroundColor: "#ddefe9", justifyContent: "center" },
  card: { minHeight: 90, padding: 16, borderRadius: 14, borderWidth: 1, borderColor: "#bdccc7", backgroundColor: "#fff" },
  title: { color: "#173b33", fontSize: 18, fontWeight: "800", marginBottom: 6 },
});

