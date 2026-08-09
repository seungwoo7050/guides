import appConfig from "../app.json";

type Plugin = string | [string, Record<string, unknown>];

function optionsFor(name: string): Record<string, unknown> {
  const entry = (appConfig.expo.plugins as Plugin[]).find(
    (candidate) => Array.isArray(candidate) && candidate[0] === name,
  );
  if (!Array.isArray(entry)) throw new Error(`missing ${name} plugin options`);
  return entry[1];
}

describe("Stage 05 CNG contract input", () => {
  it("configures a stable notification channel without remote background notifications", () => {
    expect(optionsFor("expo-notifications")).toEqual({
      defaultChannel: "field-notes-sync",
      enableBackgroundRemoteNotifications: false,
    });
    expect(appConfig.expo.android.permissions).toEqual(expect.arrayContaining([
      "android.permission.CAMERA",
      "android.permission.ACCESS_COARSE_LOCATION",
      "android.permission.ACCESS_FINE_LOCATION",
      "android.permission.POST_NOTIFICATIONS",
    ]));
  });

  it("keeps exact alarm, audio, storage, background location and foreground services forbidden", () => {
    expect(appConfig.expo.android.blockedPermissions).toEqual(expect.arrayContaining([
      "android.permission.SCHEDULE_EXACT_ALARM",
      "android.permission.USE_EXACT_ALARM",
      "android.permission.RECORD_AUDIO",
      "android.permission.READ_MEDIA_IMAGES",
      "android.permission.READ_EXTERNAL_STORAGE",
      "android.permission.WRITE_EXTERNAL_STORAGE",
      "android.permission.ACCESS_BACKGROUND_LOCATION",
      "android.permission.FOREGROUND_SERVICE",
      "android.permission.FOREGROUND_SERVICE_LOCATION",
    ]));
  });

  it("enables BGProcessing cleanup and pins runtime/update evidence", () => {
    expect(appConfig.expo.plugins).toEqual(expect.arrayContaining([
      "expo-background-task",
      "./plugins/withProcessingOnly",
    ]));
    expect(appConfig.expo.runtimeVersion).toEqual({ policy: "appVersion" });
    expect(appConfig.expo.updates).toEqual({ enabled: false });
    expect(appConfig.expo.android.versionCode).toBe(1);
    expect(appConfig.expo.ios.buildNumber).toBe("1");
  });
});
