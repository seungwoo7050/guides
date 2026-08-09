import { StyleSheet, Text, View } from "react-native";

export function StateNotice({
  title,
  message,
  kind = "info",
}: {
  title: string;
  message: string;
  kind?: "info" | "error";
}) {
  return (
    <View
      accessibilityLiveRegion="polite"
      accessibilityRole={kind === "error" ? "alert" : "summary"}
      style={[styles.notice, kind === "error" && styles.error]}
    >
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  notice: {
    padding: 16,
    borderRadius: 14,
    backgroundColor: "#e5f1ed",
    borderWidth: 1,
    borderColor: "#a4c3ba",
    gap: 5,
  },
  error: { backgroundColor: "#fff1ee", borderColor: "#d8897e" },
  title: { fontSize: 16, fontWeight: "800", color: "#173b33" },
  message: { fontSize: 15, lineHeight: 22, color: "#36564e" },
});

