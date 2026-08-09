import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerTintColor: "#173b33", headerStyle: { backgroundColor: "#f5f1e8" } }}>
        <Stack.Screen name="index" options={{ headerShown: false }} />
        <Stack.Screen name="records/index" options={{ title: "Field Notes Skeleton" }} />
        <Stack.Screen name="records/new" options={{ title: "새 기록 TODO" }} />
        <Stack.Screen name="records/[recordId]/index" options={{ title: "기록 상세 TODO" }} />
        <Stack.Screen name="records/[recordId]/edit" options={{ title: "기록 편집 TODO" }} />
        <Stack.Screen name="sync" options={{ title: "동기화 TODO" }} />
        <Stack.Screen name="settings" options={{ title: "설정" }} />
      </Stack>
    </SafeAreaProvider>
  );
}

