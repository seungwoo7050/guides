import assert from "node:assert/strict";
import { mkdtemp, readdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), "web-app-browser-harness-test-"));
const badExecutable = path.join(temporaryRoot, "not-executable-chromium");
const previousTmpdir = process.env.TMPDIR;
const previousChromium = process.env.CHROMIUM_PATH;

try {
  await writeFile(badExecutable, "not an executable\n", { mode: 0o600 });
  process.env.TMPDIR = temporaryRoot;
  process.env.CHROMIUM_PATH = badExecutable;
  const { launchBrowser } = await import("./lib/browser-harness.mjs");

  await assert.rejects(
    launchBrowser("about:blank"),
    /브라우저 process를 시작하지 못했습니다/
  );
  assert.deepEqual(await readdir(temporaryRoot), ["not-executable-chromium"]);
  console.log("BROWSER HARNESS FAILURE CLEANUP SELF-TEST PASS");
} finally {
  if (previousTmpdir === undefined) delete process.env.TMPDIR;
  else process.env.TMPDIR = previousTmpdir;
  if (previousChromium === undefined) delete process.env.CHROMIUM_PATH;
  else process.env.CHROMIUM_PATH = previousChromium;
  await rm(temporaryRoot, { recursive: true, force: true });
}
