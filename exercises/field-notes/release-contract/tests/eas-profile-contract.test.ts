import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import {
  parseAndValidateEasProfileJson,
  validateEasProfileConfiguration,
} from "../src/index.ts";

async function textFixture(relativePath: string): Promise<string> {
  return readFile(new URL(relativePath, import.meta.url), "utf8");
}

function asObject(value: unknown): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new TypeError("test fixture object expected");
  }
  return value as Record<string, unknown>;
}

async function actualConfig(): Promise<Record<string, unknown>> {
  return asObject(
    JSON.parse(await textFixture("../../reference/eas.json")) as unknown,
  );
}

function profile(
  root: Record<string, unknown>,
  name: string,
): Record<string, unknown> {
  return asObject(asObject(root.build)[name]);
}

test("actual eas.json resolves three distinct profiles through the Node 24 base", async () => {
  const result = validateEasProfileConfiguration(await actualConfig());
  assert.equal(result.ok, true);
  if (!result.ok) return;

  const development = result.assessment.profiles.development;
  const preview = result.assessment.profiles.preview;
  const production = result.assessment.profiles.production;
  assert.ok(development !== undefined);
  assert.ok(preview !== undefined);
  assert.ok(production !== undefined);

  assert.deepEqual(development.inheritanceChain, ["base", "development"]);
  assert.deepEqual(development.node, {
    root: "24.19.0",
    android: "24.19.0",
    ios: "24.19.0",
    inherited: true,
  });
  assert.equal(development.developmentClient, true);
  assert.deepEqual(development.distribution, {
    android: "internal",
    ios: "internal",
    androidDefaulted: false,
    iosDefaulted: false,
  });
  assert.deepEqual(development.androidBuild, {
    type: "apk",
    source: "development-client",
  });

  assert.equal(preview.developmentClient, false);
  assert.equal(preview.distribution.android, "internal");
  assert.deepEqual(preview.androidBuild, {
    type: "apk",
    source: "explicit",
  });

  assert.equal(production.developmentClient, false);
  assert.deepEqual(production.distribution, {
    android: "store",
    ios: "store",
    androidDefaulted: true,
    iosDefaulted: true,
  });
  assert.deepEqual(production.androidBuild, {
    type: "app-bundle",
    source: "eas-default",
  });
  assert.deepEqual(result.assessment.sourcePolicy, {
    requireCommit: true,
    appVersionSource: "local",
  });
});

test("a valid profile assessment still makes every external guarantee false", async () => {
  const result = validateEasProfileConfiguration(await actualConfig());
  assert.equal(result.ok, true);
  if (!result.ok) return;
  assert.deepEqual(result.assessment.guarantees, {
    configurationShapeValidated: true,
    nativeBuildExecuted: false,
    artifactBytesProducedOrInspected: false,
    signingOrCredentialsValidated: false,
    applicationInstalledOrLaunched: false,
    storeUploadOrAcceptanceValidated: false,
    easUpdatePublishedOrDelivered: false,
    stableApprovalGranted: false,
  });
});

test("known-wrong fixture rejects cycles, unsafe env, update channel and production APK/internal", async () => {
  const result = parseAndValidateEasProfileJson(
    await textFixture("../fixtures/eas-known-wrong.json"),
  );
  assert.equal(result.ok, false);
  if (result.ok) return;
  const joined = result.errors.join("\n");
  for (const expected of [
    "requireCommit",
    "appVersionSource",
    "inheritance cycle",
    "secret-like or API URL key",
    "URL values are forbidden",
    "EAS Update channel",
    "extra public profile",
    "effective node must be 24.19.0",
    "internal production is forbidden",
    "production APK is forbidden",
  ]) {
    assert.match(joined, new RegExp(expected));
  }
  assert.equal(result.assessment.guarantees.nativeBuildExecuted, false);
  assert.equal(result.assessment.guarantees.storeUploadOrAcceptanceValidated, false);
});

test("unknown parent and a missing public profile are rejected before inheritance", async () => {
  const unknownParent = await actualConfig();
  profile(unknownParent, "preview").extends = "missing-base";
  const unknownResult = validateEasProfileConfiguration(unknownParent);
  assert.equal(unknownResult.ok, false);
  if (!unknownResult.ok) {
    assert.ok(unknownResult.errors.some((error) => error.includes("unknown profile")));
  }

  const missing = await actualConfig();
  delete asObject(missing.build).production;
  const missingResult = validateEasProfileConfiguration(missing);
  assert.equal(missingResult.ok, false);
  if (!missingResult.ok) {
    assert.ok(
      missingResult.errors.some((error) =>
        error.includes("production: required public profile is missing"),
      ),
    );
  }
});

test("profile and platform overrides cannot bypass the inherited Node pin", async () => {
  const rootOverride = await actualConfig();
  profile(rootOverride, "preview").node = "24.18.0";
  const rootResult = validateEasProfileConfiguration(rootOverride);
  assert.equal(rootResult.ok, false);
  if (!rootResult.ok) {
    assert.ok(rootResult.errors.some((error) => error.includes("effective root node")));
  }

  const platformOverride = await actualConfig();
  profile(platformOverride, "production").ios = { node: "22.0.0" };
  const platformResult = validateEasProfileConfiguration(platformOverride);
  assert.equal(platformResult.ok, false);
  if (!platformResult.ok) {
    assert.ok(
      platformResult.errors.some((error) =>
        error.includes("production.ios: effective node"),
      ),
    );
  }
});

test("only one non-sensitive profile label is accepted in env", async () => {
  const secretKey = await actualConfig();
  profile(secretKey, "preview").env = {
    FIELD_NOTES_BUILD_PROFILE: "preview",
    AUTH_TOKEN: "fixture-token",
  };
  const secretResult = validateEasProfileConfiguration(secretKey);
  assert.equal(secretResult.ok, false);
  if (!secretResult.ok) {
    assert.ok(secretResult.errors.some((error) => error.includes("secret-like")));
    assert.ok(secretResult.errors.some((error) => error.includes("must contain only")));
  }

  const urlValue = await actualConfig();
  profile(urlValue, "preview").env = {
    FIELD_NOTES_BUILD_PROFILE: "https://example.invalid/preview",
  };
  const urlResult = validateEasProfileConfiguration(urlValue);
  assert.equal(urlResult.ok, false);
  if (!urlResult.ok) {
    assert.ok(urlResult.errors.some((error) => error.includes("URL values")));
  }
});

test("invalid JSON is a redacted validation result, not an exception", () => {
  const result = parseAndValidateEasProfileJson('{"cli":');
  assert.deepEqual(result, {
    ok: false,
    errors: ["eas: invalid JSON"],
    assessment: {
      contract: "field-notes-eas-build-profiles-v1",
      configurationValid: false,
      sourcePolicy: { requireCommit: false, appVersionSource: null },
      profiles: {},
      guarantees: {
        configurationShapeValidated: false,
        nativeBuildExecuted: false,
        artifactBytesProducedOrInspected: false,
        signingOrCredentialsValidated: false,
        applicationInstalledOrLaunched: false,
        storeUploadOrAcceptanceValidated: false,
        easUpdatePublishedOrDelivered: false,
        stableApprovalGranted: false,
      },
      errors: ["eas: invalid JSON"],
    },
  });
});
