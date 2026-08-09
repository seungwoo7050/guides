import type { FieldRecord } from "@field-notes/shared";
import { Pressable, StyleSheet, Text, View } from "react-native";

const STATUS_LABEL: Record<FieldRecord["status"], string> = {
  draft: "초안",
  open: "진행 중",
  resolved: "해결됨",
};

export function RecordListItem({
  record,
  onPress,
}: {
  record: FieldRecord;
  onPress(): void;
}) {
  return (
    <Pressable
      accessibilityHint="기록 상세 화면을 엽니다"
      accessibilityLabel={`${record.title}, ${STATUS_LABEL[record.status]}`}
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && styles.pressed]}
    >
      <View style={styles.row}>
        <Text numberOfLines={2} style={styles.title}>
          {record.title}
        </Text>
        <Text style={styles.status}>{STATUS_LABEL[record.status]}</Text>
      </View>
      <Text style={styles.meta}>
        {new Date(record.observedAt).toLocaleString("ko-KR")}
      </Text>
      <Text style={styles.sync}>동기화: {record.syncState}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#bdccc7",
    backgroundColor: "#fffdf8",
    padding: 17,
    gap: 8,
    minHeight: 112,
  },
  pressed: { opacity: 0.72 },
  row: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
  },
  title: { flex: 1, fontSize: 18, lineHeight: 24, fontWeight: "800", color: "#173b33" },
  status: {
    fontSize: 13,
    fontWeight: "700",
    color: "#166b57",
    backgroundColor: "#ddefe9",
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 999,
  },
  meta: { fontSize: 14, color: "#5c716b" },
  sync: { fontSize: 13, color: "#5c716b" },
});

