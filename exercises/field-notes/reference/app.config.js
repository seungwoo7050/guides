const staticExpoConfig = require("./app.json").expo;

const PROFILE_ENV = "FIELD_NOTES_BUILD_PROFILE";

const PROFILES = Object.freeze({
  development: Object.freeze({
    name: "Field Notes Development",
    applicationId: "dev.openai.guides.fieldnotes.reference.development",
    scheme: "fieldnotes-development",
    appIdentityLabel: "development",
    backendEnvironmentLabel: "local-development",
    addGeneratedDevClientScheme: true,
  }),
  preview: Object.freeze({
    name: "Field Notes Preview",
    applicationId: "dev.openai.guides.fieldnotes.reference.preview",
    scheme: "fieldnotes-preview",
    appIdentityLabel: "preview",
    backendEnvironmentLabel: "preview-test-not-configured",
    addGeneratedDevClientScheme: false,
  }),
  production: Object.freeze({
    name: "Field Notes Reference",
    applicationId: "dev.openai.guides.fieldnotes.reference",
    scheme: "fieldnotes",
    appIdentityLabel: "production",
    backendEnvironmentLabel: "production-external-not-configured",
    addGeneratedDevClientScheme: false,
  }),
});

function selectedProfile(environment = process.env) {
  const value = environment[PROFILE_ENV];
  const profileName = value === undefined ? "development" : value;
  const profile = PROFILES[profileName];
  if (profile === undefined) {
    throw new Error(
      `${PROFILE_ENV} must be exactly development, preview, or production; received ${JSON.stringify(profileName)}`,
    );
  }
  return { profileName, profile };
}

function profileDevClientPlugin(plugins, addGeneratedScheme) {
  if (!Array.isArray(plugins)) {
    throw new Error("static app config must declare the expo-dev-client plugin");
  }
  let matches = 0;
  const resolved = plugins.map((entry) => {
    const pluginName = Array.isArray(entry) ? entry[0] : entry;
    if (pluginName !== "expo-dev-client") return entry;
    matches += 1;
    const existingOptions = Array.isArray(entry) ? entry[1] : undefined;
    if (
      existingOptions !== undefined &&
      (typeof existingOptions !== "object" ||
        existingOptions === null ||
        Array.isArray(existingOptions))
    ) {
      throw new Error("expo-dev-client plugin options must be an object");
    }
    return [
      "expo-dev-client",
      { ...(existingOptions ?? {}), addGeneratedScheme },
    ];
  });
  if (matches !== 1) {
    throw new Error("static app config must declare expo-dev-client exactly once");
  }
  return resolved;
}

/**
 * Keep app.json as the common source of truth. This dynamic layer changes the
 * public identity labels that must not collide between install profiles and
 * limits expo-dev-client's generated launch scheme to development builds.
 * Backend endpoints and credentials deliberately do not belong in public app
 * config; backendEnvironmentLabel is a non-routing review label.
 */
function resolveConfig(environment = process.env, baseConfig = staticExpoConfig) {
  const { profileName, profile } = selectedProfile(environment);
  return {
    ...baseConfig,
    name: profile.name,
    scheme: profile.scheme,
    plugins: profileDevClientPlugin(
      baseConfig.plugins,
      profile.addGeneratedDevClientScheme,
    ),
    ios: {
      ...baseConfig.ios,
      bundleIdentifier: profile.applicationId,
    },
    android: {
      ...baseConfig.android,
      package: profile.applicationId,
    },
    extra: {
      ...baseConfig.extra,
      fieldNotes: {
        ...(baseConfig.extra?.fieldNotes ?? {}),
        buildProfile: profileName,
        appIdentityLabel: profile.appIdentityLabel,
        backendEnvironmentLabel: profile.backendEnvironmentLabel,
      },
    },
  };
}

module.exports = ({ config = staticExpoConfig } = {}) =>
  resolveConfig(process.env, config);

// Non-enumerable helpers let the local contract checker exercise profile
// selection without changing the public Expo config returned by the function.
Object.defineProperties(module.exports, {
  resolveConfig: { value: resolveConfig },
  selectedProfile: { value: selectedProfile },
});
