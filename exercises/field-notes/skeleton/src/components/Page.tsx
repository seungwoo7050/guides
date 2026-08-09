import type { PropsWithChildren } from "react";
import { ScrollView, StyleSheet, Text } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

export function Page({ title, children }: PropsWithChildren<{ title: string }>) {
  return (
    <SafeAreaView edges={["bottom", "left", "right"]} style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text accessibilityRole="header" style={styles.title}>{title}</Text>
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#f5f1e8" },
  content: { flexGrow: 1, padding: 20, gap: 16 },
  title: { color: "#173b33", fontSize: 30, lineHeight: 36, fontWeight: "800" },
});

