import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { assessCrossPlatform, validateReleaseEvidence } from "../src/index.ts";

async function fixture(name: string): Promise<Record<string, any>> {
  return JSON.parse(
    await readFile(new URL(`../fixtures/${name}`, import.meta.url), "utf8"),
  ) as Record<string, any>;
}

function androidInstallation(artifactRef = "android-install-apk", deviceClass = "physical") {
  return {
    status: "verified",
    artifactRef,
    deviceClass,
    deviceIdentityRedacted: "android/redacted-fixture",
    installedApplicationId: "dev.openai.guides.fieldnotes.reference",
    installedVersion: "1.0.0",
    installedBuildNumber: "42",
    observedRuntimeVersion: "runtime-fixture",
    observedRuntimeFingerprintOrPolicy: "runtime-fixture-policy-v1",
    launchResult: "passed",
    observedAt: "2026-08-09T01:05:00.000Z",
    evidenceRef: "device/android-install-fixture.md",
  };
}

function signingNotRun(artifactRef: string) {
  return {
    status: "not-run",
    artifactRef,
    reason: "synthetic fixture has no signing observation",
    requiredEvidence: "artifact-linked redacted signing identity and human review",
  };
}

test("Android candidate keeps publishing AAB and installable APK as distinct same-source artifacts", async () => {
  const result = validateReleaseEvidence(await fixture("android-aab.json"));
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.artifactRoles, {
    "android-publishing-aab": "publishing",
    "android-install-apk": "device-installable",
  });
  assert.equal(result.artifactSet.publishingOrArchiveIdentified, true);
  assert.equal(result.artifactSet.installableCandidateIdentified, true);
  assert.equal(result.artifactSet.releaseCandidateArtifactSetComplete, true);
  assert.equal(result.installationEvidenceConsistent, false);
  assert.equal(result.physicalDeviceEvidenceConsistent, false);
  assert.equal(result.storeDeliveryReviewState, "not-run");
});

test("iOS candidate keeps xcarchive and provisioned IPA distinct", async () => {
  const result = validateReleaseEvidence(await fixture("ios-ipa.json"));
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.artifactRoles["ios-archive"], "archive");
  assert.equal(result.artifactRoles["ios-install-ipa"], "device-installable");
  assert.equal(result.artifactSet.releaseCandidateArtifactSetComplete, true);
  assert.equal(result.installationEvidenceConsistent, true);
  assert.equal(result.physicalDeviceEvidenceConsistent, true);
  assert.deepEqual(result.signingSummary, { notRun: 0, claimed: 2, manuallyReviewed: 0 });
  assert.equal("signingVerified" in result, false);
});

test("directory bundles require the canonical tree identity instead of pretending to be files", async () => {
  const valid = validateReleaseEvidence(await fixture("ios-ipa.json"));
  assert.equal(valid.ok, true);
  if (!valid.ok) return;
  const archive = valid.evidence.artifacts.find(
    (artifact) => artifact.kind === "ios-xcarchive",
  );
  assert.deepEqual(archive, {
    ref: "ios-archive",
    kind: "ios-xcarchive",
    identity: "directory-tree",
    directoryName: "FieldNotes-preview.xcarchive",
    fileCount: 24,
    byteSize: 234566,
    treeSha256:
      "5656565656565656565656565656565656565656565656565656565656565656",
    treeDigestAlgorithm: "sha256-canonical-tree-v1",
  });

  const fileClaim = await fixture("ios-ipa.json");
  fileClaim.artifacts[0] = {
    ref: "ios-archive",
    kind: "ios-xcarchive",
    identity: "local-bytes",
    fileName: "FieldNotes-preview.xcarchive",
    byteSize: 234566,
    sha256:
      "5656565656565656565656565656565656565656565656565656565656565656",
  };
  const fileClaimResult = validateReleaseEvidence(fileClaim);
  assert.equal(fileClaimResult.ok, false);
  if (!fileClaimResult.ok) {
    assert.ok(
      fileClaimResult.errors.some((error) =>
        error.includes("identity: expected directory-tree"),
      ),
    );
  }

  const ambiguousArchive = await fixture("ios-ipa.json");
  ambiguousArchive.artifacts[0].directoryName =
    "FieldNotes-preview.xcarchive.zip";
  ambiguousArchive.artifacts[0].treeDigestAlgorithm = "unspecified-tree-hash";
  const ambiguousResult = validateReleaseEvidence(ambiguousArchive);
  assert.equal(ambiguousResult.ok, false);
  if (!ambiguousResult.ok) {
    assert.ok(
      ambiguousResult.errors.some((error) => error.includes("must end with .xcarchive")),
    );
    assert.ok(
      ambiguousResult.errors.some((error) =>
        error.includes("expected sha256-canonical-tree-v1"),
      ),
    );
  }
});

test("schema v2 manifests stay platform-specific before pair assessment", async () => {
  const android = await fixture("android-aab.json");
  const ios = await fixture("ios-ipa.json");
  android.artifacts.push(...ios.artifacts);
  android.signing.push(...ios.signing);

  const result = validateReleaseEvidence(android);
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.ok(
      result.errors.some((error) =>
        error.includes("ios-xcarchive does not match android"),
      ),
    );
    assert.ok(
      result.errors.some((error) => error.includes("ios-ipa does not match android")),
    );
  }
});

test("artifact refs are unique and every artifact has an explicit signing state", async () => {
  const duplicate = await fixture("android-aab.json");
  duplicate.artifacts[1].ref = "android-publishing-aab";
  const duplicateResult = validateReleaseEvidence(duplicate);
  assert.equal(duplicateResult.ok, false);
  if (!duplicateResult.ok) {
    assert.ok(duplicateResult.errors.some((error) => error.includes("duplicate ref")));
  }

  const missingSigning = await fixture("android-aab.json");
  missingSigning.signing.pop();
  const missingResult = validateReleaseEvidence(missingSigning);
  assert.equal(missingResult.ok, false);
  if (!missingResult.ok) {
    assert.ok(missingResult.errors.some((error) => error.includes("missing explicit state")));
  }
});

test("known-wrong AAB and xcarchive direct-install claims are rejected", async () => {
  const android = await fixture("android-aab.json");
  android.installation = androidInstallation("android-publishing-aab", "physical");
  const androidResult = validateReleaseEvidence(android);
  assert.equal(androidResult.ok, false);
  if (!androidResult.ok) {
    assert.ok(androidResult.errors.some((error) => error.includes("not directly installable")));
  }

  const ios = await fixture("ios-ipa.json");
  ios.installation.artifactRef = "ios-archive";
  const iosResult = validateReleaseEvidence(ios);
  assert.equal(iosResult.ok, false);
  if (!iosResult.ok) {
    assert.ok(iosResult.errors.some((error) => error.includes("not directly installable")));
  }
});

test("device matrix rejects simulator-app on physical, IPA on simulator, and APK on simulator", async () => {
  const simulatorOnPhysical = await fixture("ios-ipa.json");
  simulatorOnPhysical.artifacts.push({
    ref: "ios-simulator",
    kind: "ios-simulator-app",
    identity: "directory-tree",
    directoryName: "FieldNotes.app",
    fileCount: 12,
    byteSize: 345678,
    treeSha256: "7777777777777777777777777777777777777777777777777777777777777777",
    treeDigestAlgorithm: "sha256-canonical-tree-v1",
  });
  simulatorOnPhysical.signing.push(signingNotRun("ios-simulator"));
  simulatorOnPhysical.installation.artifactRef = "ios-simulator";
  const simulatorOnPhysicalResult = validateReleaseEvidence(simulatorOnPhysical);
  assert.equal(simulatorOnPhysicalResult.ok, false);
  if (!simulatorOnPhysicalResult.ok) {
    assert.ok(simulatorOnPhysicalResult.errors.some((error) => error.includes("requires simulator")));
  }

  const ipaOnSimulator = await fixture("ios-ipa.json");
  ipaOnSimulator.installation.deviceClass = "simulator";
  const ipaOnSimulatorResult = validateReleaseEvidence(ipaOnSimulator);
  assert.equal(ipaOnSimulatorResult.ok, false);
  if (!ipaOnSimulatorResult.ok) {
    assert.ok(ipaOnSimulatorResult.errors.some((error) => error.includes("ios-ipa requires physical")));
  }

  const apkOnSimulator = await fixture("android-aab.json");
  apkOnSimulator.installation = androidInstallation("android-install-apk", "simulator");
  const apkOnSimulatorResult = validateReleaseEvidence(apkOnSimulator);
  assert.equal(apkOnSimulatorResult.ok, false);
  if (!apkOnSimulatorResult.ok) {
    assert.ok(apkOnSimulatorResult.errors.some((error) => error.includes("android-apk requires physical or emulator")));
  }
});

test("the allowed non-physical installation paths stay explicit", async () => {
  const android = await fixture("android-aab.json");
  android.installation = androidInstallation("android-install-apk", "emulator");
  const androidResult = validateReleaseEvidence(android);
  assert.equal(androidResult.ok, true);
  if (androidResult.ok) {
    assert.equal(androidResult.installationEvidenceConsistent, true);
    assert.equal(androidResult.physicalDeviceEvidenceConsistent, false);
  }

  const ios = await fixture("ios-ipa.json");
  ios.artifacts.push({
    ref: "ios-simulator",
    kind: "ios-simulator-app",
    identity: "directory-tree",
    directoryName: "FieldNotes.app",
    fileCount: 12,
    byteSize: 345678,
    treeSha256: "7777777777777777777777777777777777777777777777777777777777777777",
    treeDigestAlgorithm: "sha256-canonical-tree-v1",
  });
  ios.signing.push(signingNotRun("ios-simulator"));
  ios.installation.artifactRef = "ios-simulator";
  ios.installation.deviceClass = "simulator";
  const iosResult = validateReleaseEvidence(ios);
  assert.equal(iosResult.ok, true);
  if (iosResult.ok) assert.equal(iosResult.physicalDeviceEvidenceConsistent, false);
});

test("runtime version, fingerprint/policy, and passed launch must match the build candidate", async () => {
  const versionMismatch = await fixture("ios-ipa.json");
  versionMismatch.installation.observedRuntimeVersion = "wrong-runtime";
  const versionResult = validateReleaseEvidence(versionMismatch);
  assert.equal(versionResult.ok, false);
  if (!versionResult.ok) {
    assert.ok(versionResult.errors.some((error) => error.includes("runtime version mismatch")));
  }

  const fingerprintMismatch = await fixture("ios-ipa.json");
  fingerprintMismatch.installation.observedRuntimeFingerprintOrPolicy = "wrong-policy";
  const fingerprintResult = validateReleaseEvidence(fingerprintMismatch);
  assert.equal(fingerprintResult.ok, false);
  if (!fingerprintResult.ok) {
    assert.ok(fingerprintResult.errors.some((error) => error.includes("runtime fingerprint/policy mismatch")));
  }

  const failedLaunch = await fixture("ios-ipa.json");
  failedLaunch.installation.launchResult = "failed";
  const launchResult = validateReleaseEvidence(failedLaunch);
  assert.equal(launchResult.ok, false);
  if (!launchResult.ok) {
    assert.ok(launchResult.errors.some((error) => error.includes("requires passed launch")));
  }
});

test("Play split evidence is linked to AAB, store build, delivered-byte declaration, and physical install", async () => {
  const raw = await fixture("android-aab.json");
  raw.artifacts.push({
    ref: "play-split-build-42",
    kind: "android-play-split-set",
    identity: "store-build",
    storeBuildRef: "play/internal/42",
    displayName: "Play internal build 42 split set",
  });
  raw.signing.push(signingNotRun("play-split-build-42"));
  raw.installation = androidInstallation("play-split-build-42", "physical");
  raw.store = {
    status: "released",
    publishingArtifactRef: "android-publishing-aab",
    storeBuildRef: "play/internal/42",
    track: "internal",
    observedAt: "2026-08-09T02:00:00.000Z",
    evidenceRef: "store/android-build-42.md",
    deliveredBytes: {
      status: "declared",
      artifactRef: "play-split-build-42",
      sha256: "8888888888888888888888888888888888888888888888888888888888888888",
      method: "tester-declared pulled split set digest",
      observedAt: "2026-08-09T02:05:00.000Z",
      evidenceRef: "store/android-delivery-42.md",
    },
  };
  const result = validateReleaseEvidence(raw);
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.artifactSet.releaseCandidateArtifactSetComplete, true);
  assert.equal(result.physicalDeviceEvidenceConsistent, true);
  assert.equal(result.storeDeliveryReviewState, "declared");
  assert.equal("storeDeliveredBytesVerified" in result, false);
});

test("TestFlight evidence links archive, uploaded IPA, store build, manual delivery review, and physical install", async () => {
  const raw = await fixture("ios-ipa.json");
  raw.artifacts.push({
    ref: "testflight-build-42",
    kind: "ios-testflight-build",
    identity: "store-build",
    storeBuildRef: "app-store-connect/42",
    displayName: "TestFlight build 42",
  });
  raw.signing.push(signingNotRun("testflight-build-42"));
  raw.installation.artifactRef = "testflight-build-42";
  raw.store = {
    status: "reviewed",
    publishingArtifactRef: "ios-install-ipa",
    storeBuildRef: "app-store-connect/42",
    track: "TestFlight internal",
    observedAt: "2026-08-09T02:00:00.000Z",
    evidenceRef: "store/ios-build-42.md",
    deliveredBytes: {
      status: "manually-reviewed",
      artifactRef: "testflight-build-42",
      sha256: "9999999999999999999999999999999999999999999999999999999999999999",
      method: "reviewer-recorded installed app package digest",
      observedAt: "2026-08-09T02:05:00.000Z",
      evidenceRef: "store/ios-delivery-42.md",
      reviewer: "release-owner/redacted",
      reviewedAt: "2026-08-09T02:10:00.000Z",
      reviewEvidenceRef: "reviews/ios-delivery-42.md",
    },
  };
  const result = validateReleaseEvidence(raw);
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.artifactSet.releaseCandidateArtifactSetComplete, true);
  assert.equal(result.physicalDeviceEvidenceConsistent, true);
  assert.equal(result.storeDeliveryReviewState, "manually-reviewed");
});

test("known-wrong store refs and local bytes presented as store-delivered are rejected", async () => {
  const wrongPublishing = await fixture("android-aab.json");
  wrongPublishing.store = {
    status: "uploaded",
    publishingArtifactRef: "android-install-apk",
    storeBuildRef: "play/internal/42",
    track: "internal",
    observedAt: "2026-08-09T02:00:00.000Z",
    evidenceRef: "store/android-build-42.md",
    deliveredBytes: {
      status: "not-run",
      reason: "delivery not observed",
      requiredEvidence: "store-generated split identity and bytes evidence",
    },
  };
  const publishingResult = validateReleaseEvidence(wrongPublishing);
  assert.equal(publishingResult.ok, false);
  if (!publishingResult.ok) {
    assert.ok(publishingResult.errors.some((error) => error.includes("requires android-aab")));
  }

  const localAsDelivered = await fixture("android-aab.json");
  localAsDelivered.store = {
    status: "released",
    publishingArtifactRef: "android-publishing-aab",
    storeBuildRef: "play/production/42",
    track: "production",
    observedAt: "2026-08-09T02:00:00.000Z",
    evidenceRef: "store/android-build-42.md",
    deliveredBytes: {
      status: "declared",
      artifactRef: "android-publishing-aab",
      sha256: "8888888888888888888888888888888888888888888888888888888888888888",
      method: "incorrectly reused upload digest",
      observedAt: "2026-08-09T02:05:00.000Z",
      evidenceRef: "store/wrong-delivery.md",
    },
  };
  const deliveryResult = validateReleaseEvidence(localAsDelivered);
  assert.equal(deliveryResult.ok, false);
  if (!deliveryResult.ok) {
    assert.ok(deliveryResult.errors.some((error) => error.includes("store-build artifact")));
  }
});

test("signing claim and manual review stay distinct and artifact-linked", async () => {
  const raw = await fixture("ios-ipa.json");
  raw.signing[1] = {
    status: "manually-reviewed",
    artifactRef: "ios-install-ipa",
    redactedIdentity: "Apple Distribution: redacted fixture",
    method: "codesign metadata observation",
    observedAt: "2026-08-09T01:00:00.000Z",
    evidenceRef: "device/ios-ipa-signing-fixture.md",
    reviewer: "release-owner/redacted",
    reviewedAt: "2026-08-09T01:10:00.000Z",
    reviewEvidenceRef: "reviews/ios-signing-fixture.md",
  };
  const result = validateReleaseEvidence(raw);
  assert.equal(result.ok, true);
  if (result.ok) {
    assert.deepEqual(result.signingSummary, { notRun: 0, claimed: 1, manuallyReviewed: 1 });
    assert.equal("signatureTrustVerified" in result, false);
  }

  const missingReviewer = structuredClone(raw);
  missingReviewer.signing[1].reviewer = "";
  const missingReviewerResult = validateReleaseEvidence(missingReviewer);
  assert.equal(missingReviewerResult.ok, false);
  if (!missingReviewerResult.ok) {
    assert.ok(missingReviewerResult.errors.some((error) => error.includes("reviewer")));
  }

  const unknownRef = structuredClone(raw);
  unknownRef.signing[1].artifactRef = "does-not-exist";
  const unknownRefResult = validateReleaseEvidence(unknownRef);
  assert.equal(unknownRefResult.ok, false);
  if (!unknownRefResult.ok) {
    assert.ok(unknownRefResult.errors.some((error) => error.includes("artifactRef does not exist")));
  }
});

test("cross-platform physical-device assessment requires valid paired artifacts, same source, and physical devices", async () => {
  const androidRaw = await fixture("android-aab.json");
  androidRaw.installation = androidInstallation();
  const iosRaw = await fixture("ios-ipa.json");
  const android = validateReleaseEvidence(androidRaw);
  const ios = validateReleaseEvidence(iosRaw);
  assert.equal(android.ok, true);
  assert.equal(ios.ok, true);
  if (!android.ok || !ios.ok) return;

  const complete = assessCrossPlatform(android.evidence, ios.evidence);
  assert.equal(complete.sameSource, true);
  assert.equal(complete.sameReleaseIdentity, true);
  assert.equal(complete.androidArtifactSetComplete, true);
  assert.equal(complete.iosArtifactSetComplete, true);
  assert.equal(complete.androidPhysicalDeviceEvidenceConsistent, true);
  assert.equal(complete.iosPhysicalDeviceEvidenceConsistent, true);
  assert.equal(complete.crossPlatformPhysicalDeviceEvidenceConsistent, true);

  const emulator = structuredClone(android.evidence);
  if (emulator.installation.status === "verified") emulator.installation.deviceClass = "emulator";
  const nonPhysical = assessCrossPlatform(emulator, ios.evidence);
  assert.equal(nonPhysical.androidPhysicalDeviceEvidenceConsistent, false);
  assert.equal(nonPhysical.crossPlatformPhysicalDeviceEvidenceConsistent, false);

  const changedSource = structuredClone(ios.evidence);
  changedSource.source.commit = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
  const mismatch = assessCrossPlatform(android.evidence, changedSource);
  assert.equal(mismatch.sameSource, false);
  assert.ok(mismatch.errors.some((error) => error.includes("same source")));

  const changedRelease = structuredClone(ios.evidence);
  changedRelease.build.profile = "production";
  changedRelease.application.version = "2.0.0";
  changedRelease.application.runtimeVersion = "runtime-v2";
  changedRelease.build.runtimeFingerprintOrPolicy = "runtime-policy-v2";
  if (changedRelease.installation.status === "verified") {
    changedRelease.installation.installedVersion = "2.0.0";
    changedRelease.installation.observedRuntimeVersion = "runtime-v2";
    changedRelease.installation.observedRuntimeFingerprintOrPolicy =
      "runtime-policy-v2";
  }
  const releaseMismatch = assessCrossPlatform(
    android.evidence,
    changedRelease,
  );
  assert.equal(releaseMismatch.sameSource, true);
  assert.equal(releaseMismatch.sameReleaseIdentity, false);
  assert.equal(releaseMismatch.crossPlatformPhysicalDeviceEvidenceConsistent, false);
  assert.ok(
    releaseMismatch.errors.some((error) =>
      error.includes("same release profile/version/runtime policy"),
    ),
  );
});

test("malformed digests, file-kind suffixes, and empty not-run reasons are rejected", async () => {
  const raw = await fixture("android-aab.json");
  raw.artifacts[0].sha256 = "not-a-digest";
  raw.artifacts[1].fileName = "wrong.aab";
  raw.signing[0].reason = "";
  const result = validateReleaseEvidence(raw);
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.ok(result.errors.some((error) => error.includes("sha256")));
    assert.ok(result.errors.some((error) => error.includes("must end with .apk")));
    assert.ok(result.errors.some((error) => error.includes("signing[0].reason")));
  }
});
