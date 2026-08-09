import { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

/**
 * Runnable starting point, intentionally not an answer: it has no validation,
 * dirty-back signal, status input, observed-time input, or error focus policy.
 */
export function RecordForm({ onSubmit }: { onSubmit(value: { title: string; notes: string }): void }) {
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  return (
    <View style={styles.form}>
      <Text style={styles.label}>제목</Text>
      <TextInput accessibilityLabel="기록 제목" onChangeText={setTitle} style={styles.input} value={title} />
      <Text style={styles.label}>메모</Text>
      <TextInput accessibilityLabel="기록 메모" multiline onChangeText={setNotes} style={[styles.input, styles.notes]} value={notes} />
      <Pressable accessibilityRole="button" onPress={() => onSubmit({ title, notes })} style={styles.button}>
        <Text style={styles.buttonText}>저장</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  form: { gap: 10 },
  label: { color: "#173b33", fontSize: 16, fontWeight: "700" },
  input: { minHeight: 48, borderWidth: 1, borderColor: "#8aa39c", borderRadius: 10, padding: 12, backgroundColor: "#fff" },
  notes: { minHeight: 120, textAlignVertical: "top" },
  button: { minHeight: 48, borderRadius: 10, padding: 12, justifyContent: "center", alignItems: "center", backgroundColor: "#166b57" },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "800" },
});

