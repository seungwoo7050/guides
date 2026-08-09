import { useRouter } from "expo-router";
import { ActionButton } from "../src/components/ActionButton";
import { Screen } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

export default function NotFoundRoute() {
  const router = useRouter();
  return (
    <Screen title="경로를 찾을 수 없습니다">
      <StateNotice
        kind="error"
        message="route contract 밖의 경로입니다. 업무 데이터를 추측하지 않고 목록으로 돌아갑니다."
        title="알 수 없는 route"
      />
      <ActionButton label="기록 목록" onPress={() => router.replace("/records")} />
    </Screen>
  );
}

