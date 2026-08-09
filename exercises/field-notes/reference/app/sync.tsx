import { useRouter } from "expo-router";
import { ActionButton } from "../src/components/ActionButton";
import { Screen } from "../src/components/Screen";
import { StateNotice } from "../src/components/StateNotice";

export default function SyncRoute() {
  const router = useRouter();
  return (
    <Screen title="동기화 상태">
      <StateNotice
        message="Stage 01에는 network transport, SQLite outbox, retry worker가 없습니다. fixture의 local-only 표시는 서버 적용 여부를 뜻하지 않습니다."
        title="아직 구현하지 않은 adapter"
      />
      <ActionButton label="기록 목록" onPress={() => router.push("/records")} variant="secondary" />
    </Screen>
  );
}

