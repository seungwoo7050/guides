import type { AccessibilityRole } from "react-native";
import { Pressable, StyleSheet, Text } from "react-native";

type ActionButtonProps = {
  label: string;
  onPress(): void;
  variant?: "primary" | "secondary" | "danger";
  accessibilityLabel?: string;
  accessibilityRole?: AccessibilityRole;
  disabled?: boolean;
  checked?: boolean;
};

export function ActionButton({
  label,
  onPress,
  variant = "primary",
  accessibilityLabel,
  accessibilityRole = "button",
  disabled = false,
  checked,
}: ActionButtonProps) {
  return (
    <Pressable
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityRole={accessibilityRole}
      accessibilityState={{ disabled, checked }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <Text style={[styles.label, variant !== "primary" && styles.darkLabel]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: 48,
    minWidth: 48,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  primary: { backgroundColor: "#166b57", borderColor: "#166b57" },
  secondary: { backgroundColor: "#fffdf8", borderColor: "#8aa39c" },
  danger: { backgroundColor: "#fff5f2", borderColor: "#b84a3a" },
  label: { color: "#ffffff", fontSize: 16, fontWeight: "700" },
  darkLabel: { color: "#173b33" },
  pressed: { opacity: 0.72 },
  disabled: { opacity: 0.45 },
});
