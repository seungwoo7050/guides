import Constants from "expo-constants";
import { Text } from "react-native";
import { Page } from "../src/components/Page";
import { TodoNotice } from "../src/components/TodoNotice";

export default function SettingsRoute() {
  return (
    <Page title="설정">
      <Text>Expo SDK {Constants.expoConfig?.sdkVersion ?? "57"}</Text>
      <TodoNotice title="후속 adapter">SQLite, media, location, sync, background, notification은 아직 연결하지 않습니다.</TodoNotice>
    </Page>
  );
}

