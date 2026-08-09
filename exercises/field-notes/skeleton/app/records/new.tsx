import { useRouter } from "expo-router";
import { Alert } from "react-native";
import { Page } from "../../src/components/Page";
import { RecordForm } from "../../src/components/RecordForm";
import { TodoNotice } from "../../src/components/TodoNotice";

export default function NewRecordRoute() {
  const router = useRouter();
  return (
    <Page title="새 기록">
      <TodoNotice title="의도적으로 미완성">
        validation, draft 보존, keyboard layout, 저장소, back decision을 구현하세요.
      </TodoNotice>
      <RecordForm onSubmit={() => {
        Alert.alert("TODO", "Stage 01 in-memory save를 구현하세요.");
        router.push("/records");
      }} />
    </Page>
  );
}

