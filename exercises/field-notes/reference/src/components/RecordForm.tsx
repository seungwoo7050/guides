import type { RecordPayload, RecordStatus } from "@field-notes/shared";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  StyleSheet,
  Text,
  TextInput,
  type TextInput as TextInputInstance,
  View,
} from "react-native";
import { ActionButton } from "./ActionButton";

export const TITLE_LIMIT = 120;

export type RecordDraft = Pick<
  RecordPayload,
  "title" | "notes" | "status" | "observedAt"
>;

export const EMPTY_RECORD_DRAFT: RecordDraft = {
  title: "",
  notes: "",
  status: "draft",
  observedAt: "2026-08-09T00:00:00.000Z",
};

type RecordFormProps = {
  initialValue?: RecordDraft;
  submitLabel?: string;
  onSubmit(value: RecordDraft): Promise<void> | void;
  onCancel(): void;
  onDirtyChange?(dirty: boolean): void;
};

function sameDraft(left: RecordDraft, right: RecordDraft): boolean {
  return (
    left.title === right.title &&
    left.notes === right.notes &&
    left.status === right.status &&
    left.observedAt === right.observedAt
  );
}

export function validateRecordDraft(draft: RecordDraft): {
  title?: string;
  observedAt?: string;
} {
  const errors: { title?: string; observedAt?: string } = {};
  if (draft.title.trim().length === 0) {
    errors.title = "제목을 입력하세요.";
  } else if ([...draft.title].length > TITLE_LIMIT) {
    errors.title = `제목은 ${TITLE_LIMIT}자 이하여야 합니다.`;
  }
  if (Number.isNaN(Date.parse(draft.observedAt))) {
    errors.observedAt = "관찰 시각을 ISO 8601 형식으로 입력하세요.";
  }
  return errors;
}

export function RecordForm({
  initialValue = EMPTY_RECORD_DRAFT,
  submitLabel = "저장",
  onSubmit,
  onCancel,
  onDirtyChange,
}: RecordFormProps) {
  const [draft, setDraft] = useState<RecordDraft>({ ...initialValue });
  const [errors, setErrors] = useState<ReturnType<typeof validateRecordDraft>>({});
  const [submitting, setSubmitting] = useState(false);
  const titleRef = useRef<TextInputInstance>(null);
  const observedAtRef = useRef<TextInputInstance>(null);
  const dirty = useMemo(() => !sameDraft(draft, initialValue), [draft, initialValue]);

  useEffect(() => {
    onDirtyChange?.(dirty);
  }, [dirty, onDirtyChange]);

  const update = <Key extends keyof RecordDraft>(key: Key, value: RecordDraft[Key]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const submit = async () => {
    const nextErrors = validateRecordDraft(draft);
    setErrors(nextErrors);
    if (nextErrors.title !== undefined) {
      titleRef.current?.focus();
      return;
    }
    if (nextErrors.observedAt !== undefined) {
      observedAtRef.current?.focus();
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit({
        ...draft,
        title: draft.title.trim(),
        notes: draft.notes.trim(),
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <View style={styles.form}>
      <View style={styles.field}>
        <Text style={styles.label}>제목</Text>
        <TextInput
          accessibilityLabel="기록 제목"
          accessibilityHint={errors.title}
          maxLength={TITLE_LIMIT + 20}
          onChangeText={(value) => update("title", value)}
          ref={titleRef}
          returnKeyType="next"
          style={[styles.input, errors.title && styles.invalid]}
          value={draft.title}
        />
        {errors.title ? (
          <Text accessibilityRole="alert" style={styles.error}>
            {errors.title}
          </Text>
        ) : null}
      </View>

      <View style={styles.field}>
        <Text style={styles.label}>메모</Text>
        <TextInput
          accessibilityLabel="기록 메모"
          multiline
          onChangeText={(value) => update("notes", value)}
          style={[styles.input, styles.notes]}
          textAlignVertical="top"
          value={draft.notes}
        />
      </View>

      <View accessibilityRole="radiogroup" style={styles.field}>
        <Text style={styles.label}>상태</Text>
        <View style={styles.statusRow}>
          {(
            [
              ["draft", "초안"],
              ["open", "진행 중"],
              ["resolved", "해결됨"],
            ] as const satisfies readonly (readonly [RecordStatus, string])[]
          ).map(([value, label]) => (
            <ActionButton
              accessibilityLabel={`상태: ${label}${draft.status === value ? ", 선택됨" : ""}`}
              accessibilityRole="radio"
              checked={draft.status === value}
              key={value}
              label={label}
              onPress={() => update("status", value)}
              variant={draft.status === value ? "primary" : "secondary"}
            />
          ))}
        </View>
      </View>

      <View style={styles.field}>
        <Text style={styles.label}>관찰 시각</Text>
        <TextInput
          accessibilityLabel="관찰 시각 ISO 8601"
          accessibilityHint={errors.observedAt}
          autoCapitalize="none"
          onChangeText={(value) => update("observedAt", value)}
          ref={observedAtRef}
          style={[styles.input, errors.observedAt && styles.invalid]}
          value={draft.observedAt}
        />
        {errors.observedAt ? (
          <Text accessibilityRole="alert" style={styles.error}>
            {errors.observedAt}
          </Text>
        ) : null}
      </View>

      <View style={styles.actions}>
        <ActionButton
          disabled={submitting}
          label={submitting ? "저장 중…" : submitLabel}
          onPress={() => void submit()}
        />
        <ActionButton label="취소" onPress={onCancel} variant="secondary" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  form: { gap: 20 },
  field: { gap: 8 },
  label: { color: "#173b33", fontSize: 16, fontWeight: "800" },
  input: {
    minHeight: 50,
    borderWidth: 1,
    borderColor: "#8aa39c",
    backgroundColor: "#fffdf8",
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: "#172d28",
    fontSize: 16,
  },
  notes: { minHeight: 140 },
  invalid: { borderColor: "#b84a3a", borderWidth: 2 },
  error: { color: "#9f3327", fontSize: 14, fontWeight: "700" },
  statusRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 10, paddingBottom: 24 },
});
