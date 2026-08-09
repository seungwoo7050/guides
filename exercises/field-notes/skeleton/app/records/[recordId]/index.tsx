import { useLocalSearchParams, useRouter } from "expo-router";
import { Pressable, StyleSheet, Text } from "react-native";
import { Page } from "../../../src/components/Page";
import { TodoNotice } from "../../../src/components/TodoNotice";

export default function DetailRoute() {
  const router = useRouter();
  const { recordId } = useLocalSearchParams<{ recordId?: string | string[] }>();
  const rawId = Array.isArray(recordId) ? recordId[0] : recordId;
  return (
    <Page title="기록 상세 TODO">
      <TodoNotice title="target resolution 미완성">
        route ID를 검증하고 repository 준비 뒤 존재 여부를 확인하세요. record object를 parameter로 전달하지 마세요.
      </TodoNotice>
      <Text selectable>raw recordId: {rawId ?? "없음"}</Text>
      <Pressable accessibilityRole="button" onPress={() => router.push(`/records/${String(rawId ?? "invalid")}/edit`)} style={styles.button}><Text>편집 TODO</Text></Pressable>
    </Page>
  );
}

const styles = StyleSheet.create({ button: { minHeight: 48, padding: 14, borderRadius: 10, backgroundColor: "#ddefe9", justifyContent: "center" } });

