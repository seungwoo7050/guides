import type {
  ArtifactKind,
  ArtifactRole,
  CrossPlatformAssessment,
  InstallationCheck,
  ManualCheck,
  Platform,
  ReleaseEvidence,
  StoreCheck,
  ValidationResult,
} from "./types.ts";

type JsonObject = Record<string, unknown>;

const SHA256 = /^[a-f0-9]{64}$/;
const COMMIT = /^[a-f0-9]{7,64}$/;

const ARTIFACTS: Record<ArtifactKind, { platform: Platform; role: ArtifactRole }> = {
  "android-aab": { platform: "android", role: "publishing" },
  "android-apk": { platform: "android", role: "device-installable" },
  "ios-xcarchive": { platform: "ios", role: "archive" },
  "ios-ipa": { platform: "ios", role: "device-installable" },
  "ios-simulator-app": { platform: "ios", role: "simulator-installable" },
};

function object(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function nonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function isoDate(value: unknown): value is string {
  return nonEmpty(value) && Number.isFinite(Date.parse(value));
}

function exactKeys(value: JsonObject, keys: readonly string[], path: string, errors: string[]): void {
  const expected = new Set(keys);
  for (const key of Object.keys(value)) {
    if (!expected.has(key)) errors.push(`${path}.${key}: unexpected field`);
  }
  for (const key of keys) {
    if (!(key in value)) errors.push(`${path}.${key}: missing field`);
  }
}

function readObject(value: unknown, path: string, errors: string[]): JsonObject {
  if (!object(value)) {
    errors.push(`${path}: expected object`);
    return {};
  }
  return value;
}

function requiredText(value: unknown, path: string, errors: string[]): string {
  if (!nonEmpty(value)) {
    errors.push(`${path}: expected non-empty string`);
    return "";
  }
  return value;
}

function digest(value: unknown, path: string, errors: string[]): string {
  const text = requiredText(value, path, errors).toLowerCase();
  if (text && !SHA256.test(text)) errors.push(`${path}: expected lowercase sha256`);
  return text;
}

function parseNotRun(
  input: JsonObject,
  path: string,
  errors: string[],
): Extract<ManualCheck, { status: "not-run" }> {
  exactKeys(input, ["status", "reason", "requiredEvidence"], path, errors);
  if (input.status !== "not-run") errors.push(`${path}.status: expected not-run`);
  return {
    status: "not-run",
    reason: requiredText(input.reason, `${path}.reason`, errors),
    requiredEvidence: requiredText(input.requiredEvidence, `${path}.requiredEvidence`, errors),
  };
}

function parseManual(value: unknown, path: string, errors: string[]): ManualCheck {
  const input = readObject(value, path, errors);
  if (input.status === "verified") {
    exactKeys(input, ["status", "method", "observedAt", "evidenceRef"], path, errors);
    const observedAt = requiredText(input.observedAt, `${path}.observedAt`, errors);
    if (observedAt && !isoDate(observedAt)) errors.push(`${path}.observedAt: expected timestamp`);
    return {
      status: "verified",
      method: requiredText(input.method, `${path}.method`, errors),
      observedAt,
      evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
    };
  }
  return parseNotRun(input, path, errors);
}

function parseInstallation(value: unknown, errors: string[]): InstallationCheck {
  const path = "installation";
  const input = readObject(value, path, errors);
  if (input.status !== "verified") return parseNotRun(input, path, errors);
  exactKeys(
    input,
    [
      "status",
      "deviceClass",
      "deviceIdentityRedacted",
      "installedApplicationId",
      "installedVersion",
      "installedBuildNumber",
      "observedAt",
      "evidenceRef",
    ],
    path,
    errors,
  );
  if (!(["physical", "emulator", "simulator"] as unknown[]).includes(input.deviceClass)) {
    errors.push(`${path}.deviceClass: unsupported value`);
  }
  const observedAt = requiredText(input.observedAt, `${path}.observedAt`, errors);
  if (observedAt && !isoDate(observedAt)) errors.push(`${path}.observedAt: expected timestamp`);
  return {
    status: "verified",
    deviceClass:
      input.deviceClass === "physical" || input.deviceClass === "emulator"
        ? input.deviceClass
        : "simulator",
    deviceIdentityRedacted: requiredText(input.deviceIdentityRedacted, `${path}.deviceIdentityRedacted`, errors),
    installedApplicationId: requiredText(input.installedApplicationId, `${path}.installedApplicationId`, errors),
    installedVersion: requiredText(input.installedVersion, `${path}.installedVersion`, errors),
    installedBuildNumber: requiredText(input.installedBuildNumber, `${path}.installedBuildNumber`, errors),
    observedAt,
    evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
  };
}

function parseStore(value: unknown, errors: string[]): StoreCheck {
  const path = "store";
  const input = readObject(value, path, errors);
  if (input.status === "not-run" || input.status === undefined) {
    return parseNotRun(input, path, errors);
  }
  const allowed = ["uploaded", "reviewed", "released"];
  if (!allowed.includes(String(input.status))) errors.push(`${path}.status: unsupported value`);
  const keys = ["status", "track", "observedAt", "evidenceRef"];
  if (input.deliveredArtifactSha256 !== undefined) keys.push("deliveredArtifactSha256");
  exactKeys(input, keys, path, errors);
  const observedAt = requiredText(input.observedAt, `${path}.observedAt`, errors);
  if (observedAt && !isoDate(observedAt)) errors.push(`${path}.observedAt: expected timestamp`);
  const result: Exclude<StoreCheck, { status: "not-run" }> = {
    status:
      input.status === "reviewed" || input.status === "released"
        ? input.status
        : "uploaded",
    track: requiredText(input.track, `${path}.track`, errors),
    observedAt,
    evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
  };
  if (input.deliveredArtifactSha256 !== undefined) {
    result.deliveredArtifactSha256 = digest(
      input.deliveredArtifactSha256,
      `${path}.deliveredArtifactSha256`,
      errors,
    );
  }
  return result;
}

export function artifactRole(kind: ArtifactKind): ArtifactRole {
  return ARTIFACTS[kind].role;
}

export function validateReleaseEvidence(raw: unknown): ValidationResult {
  const errors: string[] = [];
  const root = readObject(raw, "evidence", errors);
  exactKeys(
    root,
    ["schemaVersion", "source", "application", "build", "artifact", "signing", "installation", "store", "limitations"],
    "evidence",
    errors,
  );
  if (root.schemaVersion !== 1) errors.push("schemaVersion: expected 1");

  const source = readObject(root.source, "source", errors);
  exactKeys(source, ["commit", "treeSha256", "packageLockSha256"], "source", errors);
  const commit = requiredText(source.commit, "source.commit", errors).toLowerCase();
  if (commit && !COMMIT.test(commit)) errors.push("source.commit: expected hexadecimal revision");

  const application = readObject(root.application, "application", errors);
  exactKeys(application, ["platform", "applicationId", "version", "buildNumber", "runtimeVersion"], "application", errors);
  const platform: Platform = application.platform === "ios" ? "ios" : "android";
  if (application.platform !== "android" && application.platform !== "ios") {
    errors.push("application.platform: expected android or ios");
  }

  const build = readObject(root.build, "build", errors);
  exactKeys(build, ["profile", "tool", "generatedConfigSha256", "nativeBoundaryReviewRef"], "build", errors);
  if (!(["development", "preview", "production"] as unknown[]).includes(build.profile)) {
    errors.push("build.profile: unsupported value");
  }

  const artifact = readObject(root.artifact, "artifact", errors);
  exactKeys(artifact, ["kind", "fileName", "byteSize", "sha256"], "artifact", errors);
  const kind = artifact.kind as ArtifactKind;
  if (!(kind in ARTIFACTS)) errors.push("artifact.kind: unsupported value");
  if (!Number.isInteger(artifact.byteSize) || (artifact.byteSize as number) <= 0) {
    errors.push("artifact.byteSize: expected positive integer");
  }

  const signing = parseManual(root.signing, "signing", errors);
  const installation = parseInstallation(root.installation, errors);
  const store = parseStore(root.store, errors);
  const limitations = Array.isArray(root.limitations)
    ? root.limitations.map((item, index) => requiredText(item, `limitations[${index}]`, errors))
    : (errors.push("limitations: expected array"), []);
  if (limitations.length === 0) errors.push("limitations: at least one known limit is required");

  const rule = ARTIFACTS[kind];
  if (rule !== undefined && rule.platform !== platform) {
    errors.push(`artifact.kind: ${kind} does not match ${platform}`);
  }
  if (installation.status === "verified") {
    if (rule?.role === "publishing" || rule?.role === "archive") {
      errors.push(`installation: ${kind} is not directly installable`);
    }
    if (platform === "android" && installation.deviceClass === "simulator") {
      errors.push("installation.deviceClass: Android uses physical or emulator evidence");
    }
    if (platform === "ios" && installation.deviceClass === "emulator") {
      errors.push("installation.deviceClass: iOS uses physical or simulator evidence");
    }
    if (installation.installedApplicationId !== application.applicationId) {
      errors.push("installation.installedApplicationId: application identity mismatch");
    }
    if (installation.installedVersion !== application.version) {
      errors.push("installation.installedVersion: version mismatch");
    }
    if (installation.installedBuildNumber !== application.buildNumber) {
      errors.push("installation.installedBuildNumber: build identity mismatch");
    }
  }

  const evidence: ReleaseEvidence = {
    schemaVersion: 1,
    source: {
      commit,
      treeSha256: digest(source.treeSha256, "source.treeSha256", errors),
      packageLockSha256: digest(source.packageLockSha256, "source.packageLockSha256", errors),
    },
    application: {
      platform,
      applicationId: requiredText(application.applicationId, "application.applicationId", errors),
      version: requiredText(application.version, "application.version", errors),
      buildNumber: requiredText(application.buildNumber, "application.buildNumber", errors),
      runtimeVersion: requiredText(application.runtimeVersion, "application.runtimeVersion", errors),
    },
    build: {
      profile:
        build.profile === "development" || build.profile === "production"
          ? build.profile
          : "preview",
      tool: requiredText(build.tool, "build.tool", errors),
      generatedConfigSha256: digest(build.generatedConfigSha256, "build.generatedConfigSha256", errors),
      nativeBoundaryReviewRef: requiredText(build.nativeBoundaryReviewRef, "build.nativeBoundaryReviewRef", errors),
    },
    artifact: {
      kind: rule === undefined ? "android-aab" : kind,
      fileName: requiredText(artifact.fileName, "artifact.fileName", errors),
      byteSize: Number.isInteger(artifact.byteSize) ? (artifact.byteSize as number) : 0,
      sha256: digest(artifact.sha256, "artifact.sha256", errors),
    },
    signing,
    installation,
    store,
    limitations,
  };

  if (errors.length > 0 || rule === undefined) return { ok: false, errors };
  return {
    ok: true,
    evidence,
    artifactRole: rule.role,
    localArtifactIdentified: true,
    installationVerified: installation.status === "verified",
    physicalDeviceVerified:
      installation.status === "verified" && installation.deviceClass === "physical",
    storeDeliveredBytesVerified:
      store.status === "released" && store.deliveredArtifactSha256 !== undefined,
  };
}

export function assessCrossPlatform(
  left: ReleaseEvidence,
  right: ReleaseEvidence,
): CrossPlatformAssessment {
  const errors: string[] = [];
  const entries = [left, right];
  const android = entries.find((entry) => entry.application.platform === "android");
  const ios = entries.find((entry) => entry.application.platform === "ios");
  if (android === undefined) errors.push("cross-platform evidence is missing Android");
  if (ios === undefined) errors.push("cross-platform evidence is missing iOS");
  const sameSource =
    android !== undefined &&
    ios !== undefined &&
    android.source.commit === ios.source.commit &&
    android.source.treeSha256 === ios.source.treeSha256 &&
    android.source.packageLockSha256 === ios.source.packageLockSha256;
  if (android !== undefined && ios !== undefined && !sameSource) {
    errors.push("Android and iOS evidence do not identify the same source/lock state");
  }
  const androidDeviceVerified =
    android?.installation.status === "verified" &&
    android.installation.deviceClass === "physical";
  const iosDeviceVerified =
    ios?.installation.status === "verified" &&
    ios.installation.deviceClass === "physical";
  return {
    sameSource,
    androidDeviceVerified,
    iosDeviceVerified,
    crossPlatformDeviceVerified:
      sameSource && androidDeviceVerified && iosDeviceVerified,
    errors,
  };
}
