import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { createWorkspace } from "./new-workspace.mjs";

const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), "web-app-workspace-test-"));

try {
  await writeSkeleton("safe", { "README.md": "starter\n", "src/app.js": "export const ready = false;\n" });
  const destination = await createWorkspace({ root: temporaryRoot, slug: "safe", allowedSlugs: ["safe"] });
  assert.equal(await readFile(path.join(destination, "README.md"), "utf8"), "starter\n");
  assert.equal(await readFile(path.join(destination, "src/app.js"), "utf8"), "export const ready = false;\n");

  await assert.rejects(
    createWorkspace({ root: temporaryRoot, slug: "safe", allowedSlugs: ["safe"] }),
    /이미 존재.*덮어쓰지 않음/
  );
  await assert.rejects(
    createWorkspace({ root: temporaryRoot, slug: "\.\./escape", allowedSlugs: ["safe"] }),
    /하나의 안전한 path segment/
  );
  await assert.rejects(
    createWorkspace({ root: temporaryRoot, slug: "../escape", allowedSlugs: ["../escape"] }),
    /하나의 안전한 path segment/
  );

  await writeSkeleton("linked", { "README.md": "starter\n" });
  await symlink(path.join(temporaryRoot, "outside"), path.join(temporaryRoot, "exercises/linked/skeleton/outside-link"));
  await assert.rejects(
    createWorkspace({ root: temporaryRoot, slug: "linked", allowedSlugs: ["linked"] }),
    /symbolic link를 복사하지 않습니다/
  );
  await assert.rejects(readFile(path.join(temporaryRoot, "exercises/linked/work/README.md")), /ENOENT/);

  console.log("WORKSPACE HELPER SELF-TEST PASS");
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}

async function writeSkeleton(slug, files) {
  const skeleton = path.join(temporaryRoot, "exercises", slug, "skeleton");
  await mkdir(skeleton, { recursive: true });
  for (const [relative, source] of Object.entries(files)) {
    const target = path.join(skeleton, relative);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, source);
  }
}
