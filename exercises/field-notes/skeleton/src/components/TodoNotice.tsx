import { StyleSheet, Text, View } from "react-native";

export function TodoNotice({ title, children }: { title: string; children: string }) {
  return (
    <View accessibilityRole="summary" style={styles.notice}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  notice: {
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "#bc8b42",
    backgroundColor: "#fff7dd",
    padding: 16,
    gap: 6,
  },
  title: { color: "#4c3512", fontSize: 16, fontWeight: "800" },
  body: { color: "#5e4721", fontSize: 15, lineHeight: 22 },
});

