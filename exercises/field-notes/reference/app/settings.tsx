import Constants from "expo-constants";
import { StyleSheet, Text, View } from "react-native";
import { useAppRuntime } from "../src/application/AppRuntime";
import { Screen } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

export default function SettingsRoute() {
  const { appState } = useAppRuntime();
  return (
    <Screen title="설정">
      <View style={styles.card}>
        <Text style={styles.label}>앱 버전</Text>
        <Text style={styles.value}>{Constants.expoConfig?.version ?? "unknown"}</Text>
        <Text style={styles.label}>runtime</Text>
        <Text style={styles.value}>Expo SDK 57 · React Native 0.86</Text>
        <Text style={styles.label}>저장소</Text>
        <Text style={styles.value}>Stage 01 in-memory fixture</Text>
        <Text style={styles.label}>관찰한 app lifecycle</Text>
        <Text style={styles.value}>{appState}</Text>
      </View>
      <StateNotice
        message="SQLite, camera, photo picker, location, background scheduler, notification, SyncTransport는 다음 Stage의 명시적 TODO입니다. lifecycle 변화는 관찰만 하며 background callback에 저장을 맡기지 않습니다."
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
