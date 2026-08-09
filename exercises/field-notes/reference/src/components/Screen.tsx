import type { PropsWithChildren, ReactNode } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

type ScreenProps = PropsWithChildren<{
  title: string;
  description?: string;
  headerAction?: ReactNode;
  keyboardAware?: boolean;
}>;

export function Screen({
  title,
  description,
  headerAction,
  keyboardAware = false,
  children,
}: ScreenProps) {
  const body = (
    <ScrollView
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      automaticallyAdjustKeyboardInsets={keyboardAware}
    >
      <View style={styles.header}>
        <View style={styles.headingCopy}>
          <Text accessibilityRole="header" style={styles.title}>
            {title}
          </Text>
          {description ? <Text style={styles.description}>{description}</Text> : null}
        </View>
        {headerAction}
      </View>
      {children}
    </ScrollView>
  );

  return (
    <SafeAreaView edges={["bottom", "left", "right"]} style={styles.safeArea}>
      {keyboardAware ? (
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.flex}
        >
          {body}
        </KeyboardAvoidingView>
      ) : (
        body
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#f5f1e8" },
  flex: { flex: 1 },
  content: { padding: 20, gap: 16, flexGrow: 1 },
  header: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
  },
  headingCopy: { flex: 1, minWidth: 220, gap: 6 },
  title: { fontSize: 30, lineHeight: 36, fontWeight: "800", color: "#173b33" },
  description: { fontSize: 16, lineHeight: 23, color: "#47645d" },
});

