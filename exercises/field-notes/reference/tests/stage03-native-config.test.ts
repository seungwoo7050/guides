import appConfig from "../app.json";

type PluginTuple = [string, Record<string, unknown>];

function plugin(name: string): Record<string, unknown> {
  const plugins = appConfig.expo.plugins as unknown as Array<string | PluginTuple>;
  const match = plugins.find(
    (entry): entry is PluginTuple => Array.isArray(entry) && entry[0] === name,
  );
  if (match === undefined) throw new Error(`missing config plugin ${name}`);
  return match[1];
}

describe("Stage 03 CNG input", () => {
  it("declares contextual camera/picker text while blocking microphone", () => {
    const imagePicker = plugin("expo-image-picker");
    expect(imagePicker.cameraPermission).toEqual(expect.stringContaining("선택"));
    expect(imagePicker.photosPermission).toEqual(expect.stringContaining("고른 사진"));
    expect(imagePicker.microphonePermission).toBe(false);
  });

  it("enables when-in-use location only and explicitly disables background/service modes", () => {
    const location = plugin("expo-location");
    expect(location.locationWhenInUsePermission).toEqual(
      expect.stringContaining("선택"),
    );
    expect(location.locationAlwaysAndWhenInUsePermission).toBe(false);
    expect(location.locationAlwaysPermission).toBe(false);
    expect(location.isIosBackgroundLocationEnabled).toBe(false);
    expect(location.isAndroidBackgroundLocationEnabled).toBe(false);
    expect(location.isAndroidForegroundServiceEnabled).toBe(false);
  });

  it("blocks broad media, audio, background location, and location service permissions", () => {
    expect(appConfig.expo.android.permissions).toEqual(
      expect.arrayContaining([
        "android.permission.CAMERA",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.ACCESS_FINE_LOCATION",
      ]),
    );
    expect(appConfig.expo.android.blockedPermissions).toEqual(
      expect.arrayContaining([
        "android.permission.RECORD_AUDIO",
        "android.permission.READ_MEDIA_IMAGES",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.ACCESS_BACKGROUND_LOCATION",
        "android.permission.FOREGROUND_SERVICE",
        "android.permission.FOREGROUND_SERVICE_LOCATION",
      ]),
    );
  });
});
