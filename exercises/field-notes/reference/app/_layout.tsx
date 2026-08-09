import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AppRuntimeProvider } from "../src/application/AppRuntime";
import { StartupNavigationBridge } from "../src/application/StartupNavigationBridge";

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AppRuntimeProvider>
        <StatusBar style="auto" />
        <StartupNavigationBridge />
        <Stack
          screenOptions={{
            headerBackButtonDisplayMode: "minimal",
            headerBackButtonMenuEnabled: false,
            headerStyle: { backgroundColor: "#f5f1e8" },
            headerTintColor: "#173b33",
            headerTitleStyle: { fontWeight: "800" },
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="records/index" options={{ title: "Field Notes" }} />
          <Stack.Screen name="records/new" options={{ title: "새 기록" }} />
          <Stack.Screen
            name="records/[recordId]/index"
            options={{ title: "기록 상세" }}
          />
          <Stack.Screen
            name="records/[recordId]/edit"
            options={{ title: "기록 편집" }}
          />
          <Stack.Screen name="sync" options={{ title: "동기화" }} />
          <Stack.Screen name="settings" options={{ title: "설정" }} />
          <Stack.Screen name="+not-found" options={{ title: "찾을 수 없음" }} />
        </Stack>
      </AppRuntimeProvider>
    </SafeAreaProvider>
  );
}
