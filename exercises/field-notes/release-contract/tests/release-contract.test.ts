import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { assessCrossPlatform, validateReleaseEvidence } from "../src/index.ts";

async function fixture(name: string): Promise<unknown> {
  return JSON.parse(
    await readFile(new URL(`../fixtures/${name}`, import.meta.url), "utf8"),
  );
}

test("AAB is classified as publishing evidence and leaves install explicitly not-run", async () => {
  const result = validateReleaseEvidence(await fixture("android-aab.json"));
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.artifactRole, "publishing");
  assert.equal(result.installationVerified, false);
  assert.equal(result.physicalDeviceVerified, false);
  assert.equal(result.storeDeliveredBytesVerified, false);
});

test("a provisioned IPA can carry separate physical-device install evidence", async () => {
  const result = validateReleaseEvidence(await fixture("ios-ipa.json"));
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.equal(result.artifactRole, "device-installable");
  assert.equal(result.installationVerified, true);
  assert.equal(result.physicalDeviceVerified, true);
});

test("known-wrong AAB-as-installed evidence is rejected", async () => {
  const raw = (await fixture("android-aab.json")) as Record<string, unknown>;
  raw.installation = {
    status: "verified",
    deviceClass: "physical",
    deviceIdentityRedacted: "android/redacted",
    installedApplicationId: "dev.openai.guides.fieldnotes.reference",
    installedVersion: "1.0.0",
    installedBuildNumber: "42",
    observedAt: "2026-08-09T01:00:00.000Z",
    evidenceRef: "device/android-install.md",
  };
  const result = validateReleaseEvidence(raw);
  assert.equal(result.ok, false);
  if (!result.ok) assert.ok(result.errors.some((error) => error.includes("not directly installable")));
});

test("empty not-run reason and malformed digest are rejected", async () => {
  const raw = (await fixture("android-aab.json")) as Record<string, any>;
  raw.signing.reason = "";
  raw.artifact.sha256 = "not-a-digest";
  const result = validateReleaseEvidence(raw);
  assert.equal(result.ok, false);
  if (!result.ok) {
    assert.ok(result.errors.some((error) => error.includes("signing.reason")));
    assert.ok(result.errors.some((error) => error.includes("artifact.sha256")));
  }
});

test("installation identity must equal the built application identity", async () => {
  const raw = (await fixture("ios-ipa.json")) as Record<string, any>;
  raw.installation.installedBuildNumber = "different";
  const result = validateReleaseEvidence(raw);
  assert.equal(result.ok, false);
  if (!result.ok) assert.ok(result.errors.some((error) => error.includes("build identity mismatch")));
});

test("cross-platform completion requires the same source and both device checks", async () => {
  const androidResult = validateReleaseEvidence(await fixture("android-aab.json"));
  const iosResult = validateReleaseEvidence(await fixture("ios-ipa.json"));
  assert.equal(androidResult.ok, true);
  assert.equal(iosResult.ok, true);
  if (!androidResult.ok || !iosResult.ok) return;
  const incomplete = assessCrossPlatform(androidResult.evidence, iosResult.evidence);
  assert.equal(incomplete.sameSource, true);
  assert.equal(incomplete.crossPlatformDeviceVerified, false);

  const changed = structuredClone(iosResult.evidence);
  changed.source.commit = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
  const mismatch = assessCrossPlatform(androidResult.evidence, changed);
  assert.equal(mismatch.sameSource, false);
  assert.ok(mismatch.errors.some((error) => error.includes("same source")));
});
