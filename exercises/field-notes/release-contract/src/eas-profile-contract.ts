import type {
  EasAndroidBuildType,
  EasAndroidProfile,
  EasBuildProfile,
  EasDistribution,
  EasPlatformProfile,
  EasProfileContractAssessment,
  EasProfileContractGuarantees,
  EasProfileValidationResult,
  PublicEasBuildProfile,
  ResolvedEasProfileAssessment,
  ValidatedEasConfiguration,
} from "./eas-profile-types.ts";

const PUBLIC_PROFILES = [
  "development",
  "preview",
  "production",
] as const satisfies readonly PublicEasBuildProfile[];
const ALLOWED_BUILD_PROFILES = new Set<string>(["base", ...PUBLIC_PROFILES]);
const NODE_PIN = "24.19.0" as const;
const PROFILE_LABEL_KEY = "FIELD_NOTES_BUILD_PROFILE";

type UnknownObject = Record<string, unknown>;

type EffectivePlatform = {
  node: string | undefined;
  distribution: EasDistribution | undefined;
  env: Record<string, string>;
};

type EffectiveAndroid = EffectivePlatform & {
  buildType: EasAndroidBuildType | undefined;
};

type EffectiveProfile = {
  chain: string[];
  node: string | undefined;
  developmentClient: boolean | undefined;
  distribution: EasDistribution | undefined;
  environment: string | undefined;
  env: Record<string, string>;
  android: EffectiveAndroid;
  ios: EffectivePlatform;
};

function isObject(value: unknown): value is UnknownObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function objectAt(
  value: unknown,
  path: string,
  errors: string[],
): UnknownObject | null {
  if (!isObject(value)) {
    errors.push(`${path}: expected an object`);
    return null;
  }
  return value;
}

function rejectUnknownKeys(
  value: UnknownObject,
  allowed: ReadonlySet<string>,
  path: string,
  errors: string[],
): void {
  for (const key of Object.keys(value)) {
    if (!allowed.has(key)) errors.push(`${path}.${key}: unsupported key`);
  }
}

function optionalString(
  value: UnknownObject,
  key: string,
  path: string,
  errors: string[],
): string | undefined {
  const candidate = value[key];
  if (candidate === undefined) return undefined;
  if (typeof candidate !== "string" || candidate.length === 0) {
    errors.push(`${path}.${key}: expected a non-empty string`);
    return undefined;
  }
  return candidate;
}

function optionalBoolean(
  value: UnknownObject,
  key: string,
  path: string,
  errors: string[],
): boolean | undefined {
  const candidate = value[key];
  if (candidate === undefined) return undefined;
  if (typeof candidate !== "boolean") {
    errors.push(`${path}.${key}: expected a boolean`);
    return undefined;
  }
  return candidate;
}

function secretLikeKey(key: string): boolean {
  const upper = key.toUpperCase();
  const words = upper.split(/[^A-Z0-9]+/u);
  return (
    upper.includes("API_URL") ||
    words.some((word) =>
      [
        "SECRET",
        "TOKEN",
        "PASSWORD",
        "PASSWD",
        "CREDENTIAL",
        "CREDENTIALS",
        "AUTH",
        "PRIVATE",
        "KEY",
        "DSN",
        "CERT",
        "CERTIFICATE",
      ].includes(word),
    )
  );
}

function urlLikeValue(value: string): boolean {
  return /(?:^|\s)[a-z][a-z0-9+.-]*:\/\//iu.test(value) || /^www\./iu.test(value);
}

function secretLikeValue(value: string): boolean {
  return (
    /-----BEGIN [A-Z ]*PRIVATE KEY-----/u.test(value) ||
    /(?:^|\s)(?:bearer\s+|password\s*=)/iu.test(value) ||
    /(?:^|[^a-z0-9])(?:sk|ghp|github_pat|xox[baprs])[-_][a-z0-9_-]{8,}/iu.test(
      value,
    )
  );
}

function parseEnv(
  value: unknown,
  path: string,
  errors: string[],
): Record<string, string> | undefined {
  if (value === undefined) return undefined;
  const object = objectAt(value, path, errors);
  if (object === null) return undefined;
  const env: Record<string, string> = {};
  for (const [key, rawValue] of Object.entries(object)) {
    if (typeof rawValue !== "string") {
      errors.push(`${path}.${key}: environment value must be a string`);
      continue;
    }
    if (secretLikeKey(key)) {
      errors.push(`${path}.${key}: secret-like or API URL key is forbidden`);
    }
    if (urlLikeValue(rawValue)) {
      errors.push(`${path}.${key}: URL values are forbidden in this profile contract`);
    }
    if (secretLikeValue(rawValue)) {
      errors.push(`${path}.${key}: secret-like value is forbidden`);
    }
    env[key] = rawValue;
  }
  return env;
}

function parseDistribution(
  value: UnknownObject,
  path: string,
  errors: string[],
): EasDistribution | undefined {
  const candidate = optionalString(value, "distribution", path, errors);
  if (candidate === undefined) return undefined;
  if (candidate !== "internal" && candidate !== "store") {
    errors.push(`${path}.distribution: expected internal or store`);
    return undefined;
  }
  return candidate;
}

function parsePlatform(
  value: unknown,
  path: string,
  platform: "android" | "ios",
  errors: string[],
): EasAndroidProfile | EasPlatformProfile | undefined {
  if (value === undefined) return undefined;
  const object = objectAt(value, path, errors);
  if (object === null) return undefined;
  const allowed = new Set(["node", "distribution", "env"]);
  if (platform === "android") allowed.add("buildType");
  rejectUnknownKeys(object, allowed, path, errors);
  const node = optionalString(object, "node", path, errors);
  const distribution = parseDistribution(object, path, errors);
  const env = parseEnv(object.env, `${path}.env`, errors);
  let buildType: EasAndroidBuildType | undefined;
  if (platform === "android") {
    const candidate = optionalString(object, "buildType", path, errors);
    if (candidate === "apk" || candidate === "app-bundle") {
      buildType = candidate;
    } else if (candidate !== undefined) {
      errors.push(`${path}.buildType: expected apk or app-bundle`);
    }
  }
  return {
    ...(node === undefined ? {} : { node }),
    ...(distribution === undefined ? {} : { distribution }),
    ...(env === undefined ? {} : { env }),
    ...(buildType === undefined ? {} : { buildType }),
  };
}

function parseProfile(
  value: unknown,
  path: string,
  errors: string[],
): EasBuildProfile | null {
  const object = objectAt(value, path, errors);
  if (object === null) return null;
  rejectUnknownKeys(
    object,
    new Set([
      "extends",
      "node",
      "developmentClient",
      "distribution",
      "environment",
      "env",
      "android",
      "ios",
      "channel",
    ]),
    path,
    errors,
  );
  if (object.channel !== undefined) {
    errors.push(
      `${path}.channel: EAS Update channel is outside this build-only contract`,
    );
  }
  const parent = optionalString(object, "extends", path, errors);
  const node = optionalString(object, "node", path, errors);
  const developmentClient = optionalBoolean(
    object,
    "developmentClient",
    path,
    errors,
  );
  const distribution = parseDistribution(object, path, errors);
  const environment = optionalString(object, "environment", path, errors);
  const env = parseEnv(object.env, `${path}.env`, errors);
  const android = parsePlatform(
    object.android,
    `${path}.android`,
    "android",
    errors,
  ) as EasAndroidProfile | undefined;
  const ios = parsePlatform(
    object.ios,
    `${path}.ios`,
    "ios",
    errors,
  ) as EasPlatformProfile | undefined;
  return {
    ...(parent === undefined ? {} : { extends: parent }),
    ...(node === undefined ? {} : { node }),
    ...(developmentClient === undefined ? {} : { developmentClient }),
    ...(distribution === undefined ? {} : { distribution }),
    ...(environment === undefined ? {} : { environment }),
    ...(env === undefined ? {} : { env }),
    ...(android === undefined ? {} : { android }),
    ...(ios === undefined ? {} : { ios }),
  };
}

function emptyEffective(name: string): EffectiveProfile {
  return {
    chain: [name],
    node: undefined,
    developmentClient: undefined,
    distribution: undefined,
    environment: undefined,
    env: {},
    android: {
      node: undefined,
      distribution: undefined,
      env: {},
      buildType: undefined,
    },
    ios: { node: undefined, distribution: undefined, env: {} },
  };
}

function mergeProfile(
  parent: EffectiveProfile | null,
  name: string,
  profile: EasBuildProfile,
): EffectiveProfile {
  const base = parent ?? emptyEffective(name);
  return {
    chain: parent === null ? [name] : [...parent.chain, name],
    node: profile.node ?? base.node,
    developmentClient:
      profile.developmentClient ?? base.developmentClient,
    distribution: profile.distribution ?? base.distribution,
    environment: profile.environment ?? base.environment,
    env: { ...base.env, ...profile.env },
    android: {
      node: profile.android?.node ?? base.android.node,
      distribution:
        profile.android?.distribution ?? base.android.distribution,
      env: { ...base.android.env, ...profile.android?.env },
      buildType: profile.android?.buildType ?? base.android.buildType,
    },
    ios: {
      node: profile.ios?.node ?? base.ios.node,
      distribution: profile.ios?.distribution ?? base.ios.distribution,
      env: { ...base.ios.env, ...profile.ios?.env },
    },
  };
}

function resolveProfile(
  name: string,
  profiles: Readonly<Record<string, EasBuildProfile>>,
  cache: Map<string, EffectiveProfile>,
  stack: string[],
  errors: string[],
): EffectiveProfile | null {
  const cached = cache.get(name);
  if (cached !== undefined) return cached;
  const cycleStart = stack.indexOf(name);
  if (cycleStart >= 0) {
    errors.push(
      `build.${name}.extends: inheritance cycle ${[
        ...stack.slice(cycleStart),
        name,
      ].join(" -> ")}`,
    );
    return null;
  }
  const profile = profiles[name];
  if (profile === undefined) return null;
  let parent: EffectiveProfile | null = null;
  if (profile.extends !== undefined) {
    if (profiles[profile.extends] === undefined) {
      errors.push(
        `build.${name}.extends: unknown profile ${profile.extends}`,
      );
      return null;
    }
    parent = resolveProfile(
      profile.extends,
      profiles,
      cache,
      [...stack, name],
      errors,
    );
    if (parent === null) return null;
  }
  const resolved = mergeProfile(parent, name, profile);
  if (resolved.chain.length > 6) {
    errors.push(`build.${name}.extends: extension depth exceeds EAS limit of 5`);
    return null;
  }
  cache.set(name, resolved);
  return resolved;
}

function requireProfileLabel(
  profile: PublicEasBuildProfile,
  env: Record<string, string>,
  path: string,
  errors: string[],
): void {
  const keys = Object.keys(env);
  if (
    keys.length !== 1 ||
    keys[0] !== PROFILE_LABEL_KEY ||
    env[PROFILE_LABEL_KEY] !== profile
  ) {
    errors.push(
      `${path}: must contain only ${PROFILE_LABEL_KEY}=${profile}`,
    );
  }
}

function assessPublicProfile(
  profile: PublicEasBuildProfile,
  raw: EasBuildProfile,
  effective: EffectiveProfile,
  errors: string[],
): ResolvedEasProfileAssessment | null {
  const rootNode = effective.node;
  const androidNode = effective.android.node ?? rootNode;
  const iosNode = effective.ios.node ?? rootNode;
  if (rootNode !== NODE_PIN) {
    errors.push(`build.${profile}: effective root node must be ${NODE_PIN}`);
  }
  if (androidNode !== NODE_PIN) {
    errors.push(`build.${profile}.android: effective node must be ${NODE_PIN}`);
  }
  if (iosNode !== NODE_PIN) {
    errors.push(`build.${profile}.ios: effective node must be ${NODE_PIN}`);
  }

  const developmentClient = effective.developmentClient ?? false;
  const androidDistribution =
    effective.android.distribution ?? effective.distribution ?? "store";
  const iosDistribution =
    effective.ios.distribution ?? effective.distribution ?? "store";
  const androidDistributionDefaulted =
    effective.android.distribution === undefined &&
    effective.distribution === undefined;
  const iosDistributionDefaulted =
    effective.ios.distribution === undefined &&
    effective.distribution === undefined;

  let androidBuildType: EasAndroidBuildType;
  let androidBuildSource: ResolvedEasProfileAssessment["androidBuild"]["source"];
  if (effective.android.buildType !== undefined) {
    androidBuildType = effective.android.buildType;
    androidBuildSource = "explicit";
  } else if (developmentClient) {
    androidBuildType = "apk";
    androidBuildSource = "development-client";
  } else if (androidDistribution === "internal") {
    androidBuildType = "apk";
    androidBuildSource = "internal-distribution";
  } else {
    androidBuildType = "app-bundle";
    androidBuildSource = "eas-default";
  }

  if (effective.environment !== profile) {
    errors.push(`build.${profile}.environment: must equal ${profile}`);
  }
  requireProfileLabel(profile, effective.env, `build.${profile}.env`, errors);
  if (
    Object.keys(effective.android.env).length > 0 ||
    Object.keys(effective.ios.env).length > 0
  ) {
    errors.push(
      `build.${profile}: platform env is forbidden; keep only the root profile label`,
    );
  }

  if (profile === "development") {
    if (!developmentClient) {
      errors.push("build.development.developmentClient: must be true");
    }
    if (androidDistribution !== "internal" || iosDistribution !== "internal") {
      errors.push("build.development.distribution: both platforms must be internal");
    }
    if (androidBuildType !== "apk") {
      errors.push("build.development.android: development client must resolve to APK");
    }
  } else if (profile === "preview") {
    if (developmentClient) {
      errors.push("build.preview.developmentClient: must be false or omitted");
    }
    if (androidDistribution !== "internal" || iosDistribution !== "internal") {
      errors.push("build.preview.distribution: both platforms must be internal");
    }
    if (effective.android.buildType !== "apk") {
      errors.push("build.preview.android.buildType: must explicitly be apk");
    }
  } else {
    if (developmentClient) {
      errors.push("build.production.developmentClient: must be false or omitted");
    }
    if (androidDistribution === "internal" || iosDistribution === "internal") {
      errors.push("build.production.distribution: internal production is forbidden");
    }
    if (effective.android.buildType === "apk") {
      errors.push("build.production.android.buildType: production APK is forbidden");
    }
  }

  if (
    rootNode !== NODE_PIN ||
    androidNode !== NODE_PIN ||
    iosNode !== NODE_PIN ||
    effective.environment !== profile
  ) {
    return null;
  }
  return {
    profile,
    inheritanceChain: [...effective.chain],
    node: {
      root: NODE_PIN,
      android: NODE_PIN,
      ios: NODE_PIN,
      inherited:
        raw.node === undefined &&
        raw.android?.node === undefined &&
        raw.ios?.node === undefined,
    },
    developmentClient,
    distribution: {
      android: androidDistribution,
      ios: iosDistribution,
      androidDefaulted: androidDistributionDefaulted,
      iosDefaulted: iosDistributionDefaulted,
    },
    androidBuild: { type: androidBuildType, source: androidBuildSource },
    environment: profile,
    profileLabel: profile,
  };
}

function guarantees(
  configurationShapeValidated: boolean,
): EasProfileContractGuarantees {
  return {
    configurationShapeValidated,
    nativeBuildExecuted: false,
    artifactBytesProducedOrInspected: false,
    signingOrCredentialsValidated: false,
    applicationInstalledOrLaunched: false,
    storeUploadOrAcceptanceValidated: false,
    easUpdatePublishedOrDelivered: false,
    stableApprovalGranted: false,
  };
}

function invalidResult(input: {
  errors: string[];
  profiles?: Partial<
    Record<PublicEasBuildProfile, ResolvedEasProfileAssessment>
  >;
  requireCommit?: boolean;
  appVersionSource?: string | null;
}): EasProfileValidationResult {
  const errors = [...new Set(input.errors)];
  const assessment: EasProfileContractAssessment & {
    configurationValid: false;
    guarantees: EasProfileContractGuarantees & {
      configurationShapeValidated: false;
    };
  } = {
    contract: "field-notes-eas-build-profiles-v1",
    configurationValid: false,
    sourcePolicy: {
      requireCommit: input.requireCommit ?? false,
      appVersionSource: input.appVersionSource ?? null,
    },
    profiles: input.profiles ?? {},
    guarantees: { ...guarantees(false), configurationShapeValidated: false },
    errors,
  };
  return { ok: false, errors, assessment };
}

export function validateEasProfileConfiguration(
  input: unknown,
): EasProfileValidationResult {
  const errors: string[] = [];
  const root = objectAt(input, "eas", errors);
  if (root === null) return invalidResult({ errors });
  rejectUnknownKeys(root, new Set(["cli", "build"]), "eas", errors);

  const cli = objectAt(root.cli, "eas.cli", errors);
  let requireCommit = false;
  let appVersionSource: string | null = null;
  if (cli !== null) {
    rejectUnknownKeys(
      cli,
      new Set(["requireCommit", "appVersionSource"]),
      "eas.cli",
      errors,
    );
    if (cli.requireCommit !== true) {
      errors.push("eas.cli.requireCommit: must be true");
    } else {
      requireCommit = true;
    }
    if (typeof cli.appVersionSource !== "string") {
      errors.push("eas.cli.appVersionSource: must be local");
    } else {
      appVersionSource = cli.appVersionSource;
      if (cli.appVersionSource !== "local") {
        errors.push("eas.cli.appVersionSource: must be local");
      }
    }
  }

  const build = objectAt(root.build, "eas.build", errors);
  const profiles: Record<string, EasBuildProfile> = {};
  if (build !== null) {
    for (const name of Object.keys(build)) {
      if (!ALLOWED_BUILD_PROFILES.has(name)) {
        errors.push(
          `eas.build.${name}: extra public profile is forbidden; expected exactly development, preview and production`,
        );
        continue;
      }
      const parsed = parseProfile(build[name], `eas.build.${name}`, errors);
      if (parsed !== null) profiles[name] = parsed;
    }
    for (const name of PUBLIC_PROFILES) {
      if (build[name] === undefined) {
        errors.push(`eas.build.${name}: required public profile is missing`);
      }
    }
  }

  const base = profiles.base;
  if (
    base !== undefined &&
    (Object.keys(base.env ?? {}).length > 0 ||
      Object.keys(base.android?.env ?? {}).length > 0 ||
      Object.keys(base.ios?.env ?? {}).length > 0)
  ) {
    errors.push("eas.build.base: common base may contain tooling only, not env");
  }

  const resolvedProfiles: Partial<
    Record<PublicEasBuildProfile, ResolvedEasProfileAssessment>
  > = {};
  const cache = new Map<string, EffectiveProfile>();
  for (const name of PUBLIC_PROFILES) {
    const raw = profiles[name];
    if (raw === undefined) continue;
    const effective = resolveProfile(name, profiles, cache, [], errors);
    if (effective === null) continue;
    const assessment = assessPublicProfile(name, raw, effective, errors);
    if (assessment !== null) resolvedProfiles[name] = assessment;
  }

  const uniqueErrors = [...new Set(errors)];
  const development = profiles.development;
  const preview = profiles.preview;
  const production = profiles.production;
  if (
    uniqueErrors.length > 0 ||
    cli === null ||
    requireCommit !== true ||
    appVersionSource !== "local" ||
    development === undefined ||
    preview === undefined ||
    production === undefined
  ) {
    return invalidResult({
      errors: uniqueErrors,
      profiles: resolvedProfiles,
      requireCommit,
      appVersionSource,
    });
  }

  const config: ValidatedEasConfiguration = {
    cli: { requireCommit: true, appVersionSource: "local" },
    build: {
      development,
      preview,
      production,
      ...(base === undefined ? {} : { base }),
    },
  };
  const assessment: EasProfileContractAssessment & {
    configurationValid: true;
    guarantees: EasProfileContractGuarantees & {
      configurationShapeValidated: true;
    };
    errors: [];
  } = {
    contract: "field-notes-eas-build-profiles-v1",
    configurationValid: true,
    sourcePolicy: { requireCommit: true, appVersionSource: "local" },
    profiles: resolvedProfiles,
    guarantees: { ...guarantees(true), configurationShapeValidated: true },
    errors: [],
  };
  return { ok: true, config, assessment };
}

export function parseAndValidateEasProfileJson(
  source: string,
): EasProfileValidationResult {
  try {
    return validateEasProfileConfiguration(JSON.parse(source) as unknown);
  } catch {
    return invalidResult({ errors: ["eas: invalid JSON"] });
  }
}
