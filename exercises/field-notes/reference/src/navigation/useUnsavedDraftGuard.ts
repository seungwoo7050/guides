import { useNavigation } from "expo-router";
import { usePreventRemove } from "expo-router/build/react-navigation/core";
import { useCallback, useRef } from "react";
import { Alert } from "react-native";
import {
  handlePreventedDraftNavigation,
  OneShotNavigationPermit,
} from "./draftLeavePolicy";

export function useUnsavedDraftGuard(
  dirty: boolean,
): {
  requestLeave(): void;
  leaveAfterCommit(navigate: () => void): void;
} {
  const navigation = useNavigation();
  const permit = useRef(new OneShotNavigationPermit()).current;

  const confirmDiscard = useCallback((discard: () => void) => {
    Alert.alert(
      "저장하지 않은 변경이 있습니다",
      "이 화면을 나가면 현재 초안 변경이 사라집니다.",
      [
        { text: "계속 편집", style: "cancel" },
        { text: "변경 버리기", style: "destructive", onPress: discard },
      ],
    );
  }, []);

  usePreventRemove(dirty, ({ data }) => {
    handlePreventedDraftNavigation(
      permit,
      confirmDiscard,
      () => navigation.dispatch(data.action),
    );
  });

  const requestLeave = useCallback(() => navigation.goBack(), [navigation]);
  const leaveAfterCommit = useCallback((navigate: () => void) => {
    permit.grant();
    try {
      navigate();
    } finally {
      permit.revoke();
    }
  }, [permit]);
  return { requestLeave, leaveAfterCommit };
}
