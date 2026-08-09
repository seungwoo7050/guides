import { useNavigation } from "expo-router";
import { useCallback, useEffect, useRef } from "react";
import { Alert } from "react-native";
import { decideDraftBack } from "./stage01";

export function useUnsavedDraftGuard(dirty: boolean): () => void {
  const navigation = useNavigation();
  const bypassOnce = useRef(false);

  useEffect(() => {
    return navigation.addListener("beforeRemove", (event) => {
      if (bypassOnce.current) {
        bypassOnce.current = false;
        return;
      }
      if (decideDraftBack(dirty) === "leave") {
        return;
      }
      event.preventDefault();
      Alert.alert(
        "저장하지 않은 변경이 있습니다",
        "이 화면을 나가면 현재 초안 변경이 사라집니다.",
        [
          { text: "계속 편집", style: "cancel" },
          {
            text: "변경 버리기",
            style: "destructive",
            onPress: () => navigation.dispatch(event.data.action),
          },
        ],
      );
    });
  }, [dirty, navigation]);

  return useCallback(() => {
    bypassOnce.current = true;
  }, []);
}
