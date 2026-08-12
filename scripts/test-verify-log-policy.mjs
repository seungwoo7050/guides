import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { access, mkdtemp, readFile, rm, symlink } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const externalRoot = await mkdtemp(path.join(os.tmpdir(), "web-app-verify-log-test-"));
const internalParent = path.join(root, ".guide-tmp", `verify-log-policy-${process.pid}`);

try {
  const internal = runVerify(path.join(internalParent, "verify.log"));
  assert.equal(internal.status, 2);
  assert.match(internal.output, /저장소 밖의 경로/);
  await assert.rejects(access(internalParent), /ENOENT/);

  const missingParent = path.join(externalRoot, "missing", "verify.log");
  const missing = runVerify(missingParent);
  assert.equal(missing.status, 2);
  assert.match(missing.output, /로그 디렉터리를 먼저 만들어야/);
  await assert.rejects(access(path.dirname(missingParent)), /ENOENT/);

  const readme = path.join(root, "README.md");
  const before = await readFile(readme, "utf8");
  const linkedLog = path.join(externalRoot, "linked.log");
  await symlink(readme, linkedLog);
  const linked = runVerify(linkedLog);
  assert.equal(linked.status, 2);
  assert.match(linked.output, /symbolic link/);
  assert.equal(await readFile(readme, "utf8"), before);

  console.log("VERIFY LOG POLICY SELF-TEST PASS");
} finally {
  await rm(internalParent, { recursive: true, force: true });
  await rm(externalRoot, { recursive: true, force: true });
}

function runVerify(log) {
  const result = spawnSync("sh", [path.join(root, "verify.sh")], {
    cwd: root,
    env: { ...process.env, VERIFY_LOG: log },
    encoding: "utf8"
  });
  return { status: result.status, output: `${result.stdout ?? ""}${result.stderr ?? ""}` };
}
