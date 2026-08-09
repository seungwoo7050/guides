import type {
  ArtifactEvidence,
  ArtifactKind,
  ArtifactRole,
  ArtifactSetAssessment,
  CrossPlatformAssessment,
  DeviceClass,
  DirectoryArtifactKind,
  FileArtifactKind,
  InstallationCheck,
  NotRunCheck,
  Platform,
  ReleaseEvidence,
  SigningCheck,
  SigningSummary,
  StoreArtifactKind,
  StoreCheck,
  StoreDeliveryCheck,
  ValidationResult,
} from "./types.ts";

type JsonObject = Record<string, unknown>;

type ArtifactRule = {
  platform: Platform;
  role: ArtifactRole;
  identity: "local-bytes" | "directory-tree" | "store-build";
  installDevices: readonly DeviceClass[];
};

const SHA256 = /^[a-f0-9]{64}$/;
const COMMIT = /^[a-f0-9]{7,64}$/;

const ARTIFACTS: Record<ArtifactKind, ArtifactRule> = {
  "android-aab": {
    platform: "android",
    role: "publishing",
    identity: "local-bytes",
    installDevices: [],
  },
  "android-apk": {
    platform: "android",
    role: "device-installable",
    identity: "local-bytes",
    installDevices: ["physical", "emulator"],
  },
  "android-play-split-set": {
    platform: "android",
    role: "device-installable",
    identity: "store-build",
    installDevices: ["physical"],
  },
  "ios-xcarchive": {
    platform: "ios",
    role: "archive",
    identity: "directory-tree",
    installDevices: [],
  },
  "ios-ipa": {
    platform: "ios",
    role: "device-installable",
    identity: "local-bytes",
    installDevices: ["physical"],
  },
  "ios-testflight-build": {
    platform: "ios",
    role: "device-installable",
    identity: "store-build",
    installDevices: ["physical"],
  },
  "ios-simulator-app": {
    platform: "ios",
    role: "simulator-installable",
    identity: "directory-tree",
    installDevices: ["simulator"],
  },
};

const FILE_SUFFIX: Record<FileArtifactKind, string> = {
  "android-aab": ".aab",
  "android-apk": ".apk",
  "ios-ipa": ".ipa",
};

const DIRECTORY_SUFFIX: Record<DirectoryArtifactKind, string> = {
  "ios-xcarchive": ".xcarchive",
  "ios-simulator-app": ".app",
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

function timestamp(value: unknown, path: string, errors: string[]): string {
  const text = requiredText(value, path, errors);
  if (text && !isoDate(text)) errors.push(`${path}: expected timestamp`);
  return text;
}

function digest(value: unknown, path: string, errors: string[]): string {
  const text = requiredText(value, path, errors).toLowerCase();
  if (text && !SHA256.test(text)) errors.push(`${path}: expected lowercase sha256`);
  return text;
}

function parseNotRun(value: unknown, path: string, errors: string[]): NotRunCheck {
  const input = readObject(value, path, errors);
  exactKeys(input, ["status", "reason", "requiredEvidence"], path, errors);
  if (input.status !== "not-run") errors.push(`${path}.status: expected not-run`);
  return {
    status: "not-run",
    reason: requiredText(input.reason, `${path}.reason`, errors),
    requiredEvidence: requiredText(input.requiredEvidence, `${path}.requiredEvidence`, errors),
  };
}

function parseArtifact(value: unknown, index: number, errors: string[]): ArtifactEvidence {
  const path = `artifacts[${index}]`;
  const input = readObject(value, path, errors);
  const rawKind = requiredText(input.kind, `${path}.kind`, errors);
  const kind = rawKind as ArtifactKind;
  const rule = ARTIFACTS[kind];
  if (rule === undefined) errors.push(`${path}.kind: unsupported value`);

  if (rule?.identity === "store-build" || input.identity === "store-build") {
    exactKeys(input, ["ref", "kind", "identity", "storeBuildRef", "displayName"], path, errors);
    if (input.identity !== "store-build") errors.push(`${path}.identity: expected store-build`);
    if (rule !== undefined && rule.identity !== "store-build") {
      errors.push(`${path}.identity: ${kind} must identify local bytes`);
    }
    return {
      ref: requiredText(input.ref, `${path}.ref`, errors),
      kind: (rule?.identity === "store-build" ? kind : "android-play-split-set") as StoreArtifactKind,
      identity: "store-build",
      storeBuildRef: requiredText(input.storeBuildRef, `${path}.storeBuildRef`, errors),
      displayName: requiredText(input.displayName, `${path}.displayName`, errors),
    };
  }

  if (rule?.identity === "directory-tree" || input.identity === "directory-tree") {
    exactKeys(
      input,
      [
        "ref",
        "kind",
        "identity",
        "directoryName",
        "fileCount",
        "byteSize",
        "treeSha256",
        "treeDigestAlgorithm",
      ],
      path,
      errors,
    );
    if (input.identity !== "directory-tree") {
      errors.push(`${path}.identity: expected directory-tree`);
    }
    if (rule !== undefined && rule.identity !== "directory-tree") {
      errors.push(`${path}.identity: ${kind} must identify local file bytes`);
    }
    const directoryKind = (
      rule?.identity === "directory-tree" ? kind : "ios-xcarchive"
    ) as DirectoryArtifactKind;
    const directoryName = requiredText(
      input.directoryName,
      `${path}.directoryName`,
      errors,
    );
    if (
      directoryName &&
      !directoryName.toLowerCase().endsWith(DIRECTORY_SUFFIX[directoryKind])
    ) {
      errors.push(
        `${path}.directoryName: ${directoryKind} must end with ${DIRECTORY_SUFFIX[directoryKind]}`,
      );
    }
    if (!Number.isInteger(input.fileCount) || (input.fileCount as number) <= 0) {
      errors.push(`${path}.fileCount: expected positive integer`);
    }
    if (!Number.isInteger(input.byteSize) || (input.byteSize as number) <= 0) {
      errors.push(`${path}.byteSize: expected positive integer`);
    }
    if (input.treeDigestAlgorithm !== "sha256-canonical-tree-v1") {
      errors.push(
        `${path}.treeDigestAlgorithm: expected sha256-canonical-tree-v1`,
      );
    }
    return {
      ref: requiredText(input.ref, `${path}.ref`, errors),
      kind: directoryKind,
      identity: "directory-tree",
      directoryName,
      fileCount: Number.isInteger(input.fileCount)
        ? (input.fileCount as number)
        : 0,
      byteSize: Number.isInteger(input.byteSize)
        ? (input.byteSize as number)
        : 0,
      treeSha256: digest(input.treeSha256, `${path}.treeSha256`, errors),
      treeDigestAlgorithm: "sha256-canonical-tree-v1",
    };
  }

  exactKeys(input, ["ref", "kind", "identity", "fileName", "byteSize", "sha256"], path, errors);
  if (input.identity !== "local-bytes") errors.push(`${path}.identity: expected local-bytes`);
  if (rule !== undefined && rule.identity !== "local-bytes") {
    errors.push(`${path}.identity: ${kind} must identify a store build`);
  }
  const fileKind = (rule?.identity === "local-bytes" ? kind : "android-aab") as FileArtifactKind;
  const fileName = requiredText(input.fileName, `${path}.fileName`, errors);
  if (fileName && !fileName.toLowerCase().endsWith(FILE_SUFFIX[fileKind])) {
    errors.push(`${path}.fileName: ${fileKind} must end with ${FILE_SUFFIX[fileKind]}`);
  }
  if (!Number.isInteger(input.byteSize) || (input.byteSize as number) <= 0) {
    errors.push(`${path}.byteSize: expected positive integer`);
  }
  return {
    ref: requiredText(input.ref, `${path}.ref`, errors),
    kind: fileKind,
    identity: "local-bytes",
    fileName,
    byteSize: Number.isInteger(input.byteSize) ? (input.byteSize as number) : 0,
    sha256: digest(input.sha256, `${path}.sha256`, errors),
  };
}

function parseArtifacts(value: unknown, errors: string[]): ArtifactEvidence[] {
  if (!Array.isArray(value)) {
    errors.push("artifacts: expected array");
    return [];
  }
  if (value.length === 0) errors.push("artifacts: at least one artifact is required");
  return value.map((item, index) => parseArtifact(item, index, errors));
}

function parseSigningCheck(value: unknown, index: number, errors: string[]): SigningCheck {
  const path = `signing[${index}]`;
  const input = readObject(value, path, errors);
  if (input.status === "not-run") {
    exactKeys(input, ["status", "artifactRef", "reason", "requiredEvidence"], path, errors);
    return {
      status: "not-run",
      artifactRef: requiredText(input.artifactRef, `${path}.artifactRef`, errors),
      reason: requiredText(input.reason, `${path}.reason`, errors),
      requiredEvidence: requiredText(input.requiredEvidence, `${path}.requiredEvidence`, errors),
    };
  }
  if (input.status === "manually-reviewed") {
    exactKeys(
      input,
      [
        "status",
        "artifactRef",
        "redactedIdentity",
        "method",
        "observedAt",
        "evidenceRef",
        "reviewer",
        "reviewedAt",
        "reviewEvidenceRef",
      ],
      path,
      errors,
    );
    return {
      status: "manually-reviewed",
      artifactRef: requiredText(input.artifactRef, `${path}.artifactRef`, errors),
      redactedIdentity: requiredText(input.redactedIdentity, `${path}.redactedIdentity`, errors),
      method: requiredText(input.method, `${path}.method`, errors),
      observedAt: timestamp(input.observedAt, `${path}.observedAt`, errors),
      evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
      reviewer: requiredText(input.reviewer, `${path}.reviewer`, errors),
      reviewedAt: timestamp(input.reviewedAt, `${path}.reviewedAt`, errors),
      reviewEvidenceRef: requiredText(input.reviewEvidenceRef, `${path}.reviewEvidenceRef`, errors),
    };
  }
  if (input.status !== "claimed") errors.push(`${path}.status: expected not-run, claimed, or manually-reviewed`);
  exactKeys(
    input,
    ["status", "artifactRef", "redactedIdentity", "method", "observedAt", "evidenceRef"],
    path,
    errors,
  );
  return {
    status: "claimed",
    artifactRef: requiredText(input.artifactRef, `${path}.artifactRef`, errors),
    redactedIdentity: requiredText(input.redactedIdentity, `${path}.redactedIdentity`, errors),
    method: requiredText(input.method, `${path}.method`, errors),
    observedAt: timestamp(input.observedAt, `${path}.observedAt`, errors),
    evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
  };
}

function parseSigning(value: unknown, errors: string[]): SigningCheck[] {
  if (!Array.isArray(value)) {
    errors.push("signing: expected array");
    return [];
  }
  if (value.length === 0) errors.push("signing: every artifact needs an explicit signing state");
  return value.map((item, index) => parseSigningCheck(item, index, errors));
}

function parseInstallation(value: unknown, errors: string[]): InstallationCheck {
  const path = "installation";
  const input = readObject(value, path, errors);
  if (input.status !== "verified") return parseNotRun(input, path, errors);
  exactKeys(
    input,
    [
      "status",
      "artifactRef",
      "deviceClass",
      "deviceIdentityRedacted",
      "installedApplicationId",
      "installedVersion",
      "installedBuildNumber",
      "observedRuntimeVersion",
      "observedRuntimeFingerprintOrPolicy",
      "launchResult",
      "observedAt",
      "evidenceRef",
    ],
    path,
    errors,
  );
  const allowedDevices: DeviceClass[] = ["physical", "emulator", "simulator"];
  if (!allowedDevices.includes(input.deviceClass as DeviceClass)) {
    errors.push(`${path}.deviceClass: unsupported value`);
  }
  if (input.launchResult !== "passed") {
    errors.push(`${path}.launchResult: verified installation requires passed launch`);
  }
  return {
    status: "verified",
    artifactRef: requiredText(input.artifactRef, `${path}.artifactRef`, errors),
    deviceClass: allowedDevices.includes(input.deviceClass as DeviceClass)
      ? (input.deviceClass as DeviceClass)
      : "simulator",
    deviceIdentityRedacted: requiredText(input.deviceIdentityRedacted, `${path}.deviceIdentityRedacted`, errors),
    installedApplicationId: requiredText(input.installedApplicationId, `${path}.installedApplicationId`, errors),
    installedVersion: requiredText(input.installedVersion, `${path}.installedVersion`, errors),
    installedBuildNumber: requiredText(input.installedBuildNumber, `${path}.installedBuildNumber`, errors),
    observedRuntimeVersion: requiredText(input.observedRuntimeVersion, `${path}.observedRuntimeVersion`, errors),
    observedRuntimeFingerprintOrPolicy: requiredText(
      input.observedRuntimeFingerprintOrPolicy,
      `${path}.observedRuntimeFingerprintOrPolicy`,
      errors,
    ),
    launchResult: "passed",
    observedAt: timestamp(input.observedAt, `${path}.observedAt`, errors),
    evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
  };
}

function parseStoreDelivery(value: unknown, errors: string[]): StoreDeliveryCheck {
  const path = "store.deliveredBytes";
  const input = readObject(value, path, errors);
  if (input.status === "not-run") return parseNotRun(input, path, errors);
  if (input.status === "manually-reviewed") {
    exactKeys(
      input,
      [
        "status",
        "artifactRef",
        "sha256",
        "method",
        "observedAt",
        "evidenceRef",
        "reviewer",
        "reviewedAt",
        "reviewEvidenceRef",
      ],
      path,
      errors,
    );
    return {
      status: "manually-reviewed",
      artifactRef: requiredText(input.artifactRef, `${path}.artifactRef`, errors),
      sha256: digest(input.sha256, `${path}.sha256`, errors),
      method: requiredText(input.method, `${path}.method`, errors),
      observedAt: timestamp(input.observedAt, `${path}.observedAt`, errors),
      evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
      reviewer: requiredText(input.reviewer, `${path}.reviewer`, errors),
      reviewedAt: timestamp(input.reviewedAt, `${path}.reviewedAt`, errors),
      reviewEvidenceRef: requiredText(input.reviewEvidenceRef, `${path}.reviewEvidenceRef`, errors),
    };
  }
  if (input.status !== "declared") {
    errors.push(`${path}.status: expected not-run, declared, or manually-reviewed`);
  }
  exactKeys(
    input,
    ["status", "artifactRef", "sha256", "method", "observedAt", "evidenceRef"],
    path,
    errors,
  );
  return {
    status: "declared",
    artifactRef: requiredText(input.artifactRef, `${path}.artifactRef`, errors),
    sha256: digest(input.sha256, `${path}.sha256`, errors),
    method: requiredText(input.method, `${path}.method`, errors),
    observedAt: timestamp(input.observedAt, `${path}.observedAt`, errors),
    evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
  };
}

function parseStore(value: unknown, errors: string[]): StoreCheck {
  const path = "store";
  const input = readObject(value, path, errors);
  if (input.status !== "uploaded" && input.status !== "reviewed" && input.status !== "released") {
    return parseNotRun(input, path, errors);
  }
  exactKeys(
    input,
    [
      "status",
      "publishingArtifactRef",
      "storeBuildRef",
      "track",
      "observedAt",
      "evidenceRef",
      "deliveredBytes",
    ],
    path,
    errors,
  );
  return {
    status: input.status,
    publishingArtifactRef: requiredText(
      input.publishingArtifactRef,
      `${path}.publishingArtifactRef`,
      errors,
    ),
    storeBuildRef: requiredText(input.storeBuildRef, `${path}.storeBuildRef`, errors),
    track: requiredText(input.track, `${path}.track`, errors),
    observedAt: timestamp(input.observedAt, `${path}.observedAt`, errors),
    evidenceRef: requiredText(input.evidenceRef, `${path}.evidenceRef`, errors),
    deliveredBytes: parseStoreDelivery(input.deliveredBytes, errors),
  };
}

function assessArtifactSet(platform: Platform, artifacts: readonly ArtifactEvidence[]): ArtifactSetAssessment {
  const publishingOrArchiveIdentified = artifacts.some((artifact) =>
    platform === "android" ? artifact.kind === "android-aab" : artifact.kind === "ios-xcarchive",
  );
  const installableCandidateIdentified = artifacts.some((artifact) =>
    platform === "android"
      ? artifact.kind === "android-apk" || artifact.kind === "android-play-split-set"
      : artifact.kind === "ios-ipa" || artifact.kind === "ios-testflight-build",
  );
  return {
    publishingOrArchiveIdentified,
    installableCandidateIdentified,
    releaseCandidateArtifactSetComplete:
      publishingOrArchiveIdentified && installableCandidateIdentified,
  };
}

function summarizeSigning(signing: readonly SigningCheck[]): SigningSummary {
  return {
    notRun: signing.filter((check) => check.status === "not-run").length,
    claimed: signing.filter((check) => check.status === "claimed").length,
    manuallyReviewed: signing.filter((check) => check.status === "manually-reviewed").length,
  };
}

export function artifactRole(kind: ArtifactKind): ArtifactRole {
  return ARTIFACTS[kind].role;
}

export function validateReleaseEvidence(raw: unknown): ValidationResult {
  const errors: string[] = [];
  const root = readObject(raw, "evidence", errors);
  exactKeys(
    root,
    ["schemaVersion", "source", "application", "build", "artifacts", "signing", "installation", "store", "limitations"],
    "evidence",
    errors,
  );
  if (root.schemaVersion !== 2) errors.push("schemaVersion: expected 2");

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
  exactKeys(
    build,
    ["profile", "tool", "generatedConfigSha256", "nativeBoundaryReviewRef", "runtimeFingerprintOrPolicy"],
    "build",
    errors,
  );
  if (!(build.profile === "development" || build.profile === "preview" || build.profile === "production")) {
    errors.push("build.profile: unsupported value");
  }

  const artifacts = parseArtifacts(root.artifacts, errors);
  const signing = parseSigning(root.signing, errors);
  const installation = parseInstallation(root.installation, errors);
  const store = parseStore(root.store, errors);
  const limitations = Array.isArray(root.limitations)
    ? root.limitations.map((item, index) => requiredText(item, `limitations[${index}]`, errors))
    : (errors.push("limitations: expected array"), []);
  if (limitations.length === 0) errors.push("limitations: at least one known limit is required");

  const applicationId = requiredText(application.applicationId, "application.applicationId", errors);
  const version = requiredText(application.version, "application.version", errors);
  const buildNumber = requiredText(application.buildNumber, "application.buildNumber", errors);
  const runtimeVersion = requiredText(application.runtimeVersion, "application.runtimeVersion", errors);
  const runtimeFingerprintOrPolicy = requiredText(
    build.runtimeFingerprintOrPolicy,
    "build.runtimeFingerprintOrPolicy",
    errors,
  );

  const artifactByRef = new Map<string, ArtifactEvidence>();
  for (const artifact of artifacts) {
    if (artifactByRef.has(artifact.ref)) errors.push(`artifacts: duplicate ref ${artifact.ref}`);
    artifactByRef.set(artifact.ref, artifact);
    if (ARTIFACTS[artifact.kind].platform !== platform) {
      errors.push(`artifacts.${artifact.ref}: ${artifact.kind} does not match ${platform}`);
    }
  }

  const signingRefs = new Set<string>();
  for (const check of signing) {
    if (!artifactByRef.has(check.artifactRef)) {
      errors.push(`signing.${check.artifactRef}: artifactRef does not exist`);
    }
    if (signingRefs.has(check.artifactRef)) {
      errors.push(`signing: duplicate state for artifact ${check.artifactRef}`);
    }
    signingRefs.add(check.artifactRef);
  }
  for (const artifact of artifacts) {
    if (!signingRefs.has(artifact.ref)) {
      errors.push(`signing: missing explicit state for artifact ${artifact.ref}`);
    }
  }

  if (installation.status === "verified") {
    const installedArtifact = artifactByRef.get(installation.artifactRef);
    if (installedArtifact === undefined) {
      errors.push("installation.artifactRef: artifact does not exist");
    } else {
      const allowedDevices = ARTIFACTS[installedArtifact.kind].installDevices;
      if (!allowedDevices.includes(installation.deviceClass)) {
        const expected = allowedDevices.length === 0 ? "not directly installable" : allowedDevices.join(" or ");
        errors.push(
          `installation.deviceClass: ${installedArtifact.kind} requires ${expected}, got ${installation.deviceClass}`,
        );
      }
      if (installedArtifact.identity === "store-build") {
        if (store.status === "not-run") {
          errors.push("installation.artifactRef: store-build installation requires store evidence");
        } else if (installedArtifact.storeBuildRef !== store.storeBuildRef) {
          errors.push("installation.artifactRef: store build identity mismatch");
        }
      }
    }
    if (installation.installedApplicationId !== applicationId) {
      errors.push("installation.installedApplicationId: application identity mismatch");
    }
    if (installation.installedVersion !== version) {
      errors.push("installation.installedVersion: version mismatch");
    }
    if (installation.installedBuildNumber !== buildNumber) {
      errors.push("installation.installedBuildNumber: build identity mismatch");
    }
    if (installation.observedRuntimeVersion !== runtimeVersion) {
      errors.push("installation.observedRuntimeVersion: runtime version mismatch");
    }
    if (installation.observedRuntimeFingerprintOrPolicy !== runtimeFingerprintOrPolicy) {
      errors.push("installation.observedRuntimeFingerprintOrPolicy: runtime fingerprint/policy mismatch");
    }
  }

  const storeArtifacts = artifacts.filter((artifact) => artifact.identity === "store-build");
  if (store.status === "not-run") {
    if (storeArtifacts.length > 0) {
      errors.push("store: store-build artifacts require an explicit uploaded/reviewed/released state");
    }
  } else {
    const publishingArtifact = artifactByRef.get(store.publishingArtifactRef);
    const expectedPublishingKind: ArtifactKind = platform === "android" ? "android-aab" : "ios-ipa";
    if (publishingArtifact === undefined) {
      errors.push("store.publishingArtifactRef: artifact does not exist");
    } else if (publishingArtifact.kind !== expectedPublishingKind) {
      errors.push(
        `store.publishingArtifactRef: ${platform} store submission requires ${expectedPublishingKind}`,
      );
    }
    for (const artifact of storeArtifacts) {
      if (artifact.storeBuildRef !== store.storeBuildRef) {
        errors.push(`artifacts.${artifact.ref}.storeBuildRef: store build identity mismatch`);
      }
    }
    if (store.deliveredBytes.status !== "not-run") {
      const deliveredArtifact = artifactByRef.get(store.deliveredBytes.artifactRef);
      if (deliveredArtifact === undefined) {
        errors.push("store.deliveredBytes.artifactRef: artifact does not exist");
      } else if (deliveredArtifact.identity !== "store-build") {
        errors.push("store.deliveredBytes.artifactRef: delivered bytes must reference a store-build artifact");
      } else if (deliveredArtifact.storeBuildRef !== store.storeBuildRef) {
        errors.push("store.deliveredBytes.artifactRef: store build identity mismatch");
      }
    }
  }

  const evidence: ReleaseEvidence = {
    schemaVersion: 2,
    source: {
      commit,
      treeSha256: digest(source.treeSha256, "source.treeSha256", errors),
      packageLockSha256: digest(source.packageLockSha256, "source.packageLockSha256", errors),
    },
    application: {
      platform,
      applicationId,
      version,
      buildNumber,
      runtimeVersion,
    },
    build: {
      profile:
        build.profile === "development" || build.profile === "production"
          ? build.profile
          : "preview",
      tool: requiredText(build.tool, "build.tool", errors),
      generatedConfigSha256: digest(build.generatedConfigSha256, "build.generatedConfigSha256", errors),
      nativeBoundaryReviewRef: requiredText(build.nativeBoundaryReviewRef, "build.nativeBoundaryReviewRef", errors),
      runtimeFingerprintOrPolicy,
    },
    artifacts,
    signing,
    installation,
    store,
    limitations,
  };

  if (errors.length > 0) return { ok: false, errors };

  const artifactRoles: Record<string, ArtifactRole> = {};
  for (const artifact of artifacts) artifactRoles[artifact.ref] = ARTIFACTS[artifact.kind].role;
  return {
    ok: true,
    evidence,
    artifactRoles,
    artifactSet: assessArtifactSet(platform, artifacts),
    signingSummary: summarizeSigning(signing),
    installationEvidenceConsistent: installation.status === "verified",
    physicalDeviceEvidenceConsistent:
      installation.status === "verified" && installation.deviceClass === "physical",
    storeDeliveryReviewState:
      store.status === "not-run" ? "not-run" : store.deliveredBytes.status,
  };
}

export function assessCrossPlatform(
  left: ReleaseEvidence,
  right: ReleaseEvidence,
): CrossPlatformAssessment {
  const errors: string[] = [];
  const results = [validateReleaseEvidence(left), validateReleaseEvidence(right)];
  for (const [index, result] of results.entries()) {
    if (!result.ok) {
      for (const error of result.errors) errors.push(`evidence[${index}]: ${error}`);
    }
  }
  const valid = results.filter((result): result is Extract<ValidationResult, { ok: true }> => result.ok);
  const android = valid.find((result) => result.evidence.application.platform === "android");
  const ios = valid.find((result) => result.evidence.application.platform === "ios");
  if (android === undefined) errors.push("cross-platform evidence is missing valid Android evidence");
  if (ios === undefined) errors.push("cross-platform evidence is missing valid iOS evidence");

  const sameSource =
    android !== undefined &&
    ios !== undefined &&
    android.evidence.source.commit === ios.evidence.source.commit &&
    android.evidence.source.treeSha256 === ios.evidence.source.treeSha256 &&
    android.evidence.source.packageLockSha256 === ios.evidence.source.packageLockSha256;
  if (android !== undefined && ios !== undefined && !sameSource) {
    errors.push("Android and iOS evidence do not identify the same source/lock state");
  }

  const sameReleaseIdentity =
    android !== undefined &&
    ios !== undefined &&
    android.evidence.application.version === ios.evidence.application.version &&
    android.evidence.application.runtimeVersion ===
      ios.evidence.application.runtimeVersion &&
    android.evidence.build.profile === ios.evidence.build.profile &&
    android.evidence.build.runtimeFingerprintOrPolicy ===
      ios.evidence.build.runtimeFingerprintOrPolicy;
  if (android !== undefined && ios !== undefined && !sameReleaseIdentity) {
    errors.push(
      "Android and iOS evidence do not identify the same release profile/version/runtime policy",
    );
  }

  const androidArtifactSetComplete = android?.artifactSet.releaseCandidateArtifactSetComplete ?? false;
  const iosArtifactSetComplete = ios?.artifactSet.releaseCandidateArtifactSetComplete ?? false;
  const androidPhysicalDeviceEvidenceConsistent = android?.physicalDeviceEvidenceConsistent ?? false;
  const iosPhysicalDeviceEvidenceConsistent = ios?.physicalDeviceEvidenceConsistent ?? false;

  return {
    sameSource,
    sameReleaseIdentity,
    androidArtifactSetComplete,
    iosArtifactSetComplete,
    androidPhysicalDeviceEvidenceConsistent,
    iosPhysicalDeviceEvidenceConsistent,
    crossPlatformPhysicalDeviceEvidenceConsistent:
      sameSource &&
      sameReleaseIdentity &&
      androidArtifactSetComplete &&
      iosArtifactSetComplete &&
      androidPhysicalDeviceEvidenceConsistent &&
      iosPhysicalDeviceEvidenceConsistent,
    errors,
  };
}
