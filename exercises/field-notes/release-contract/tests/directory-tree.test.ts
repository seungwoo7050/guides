import assert from "node:assert/strict";
import {
  chmod,
  mkdir,
  mkdtemp,
  rm,
  symlink,
  utimes,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { digestDirectoryTree } from "../src/directory-tree.ts";

test("canonical directory identity is sorted and includes file modes and symlink targets", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "field-notes-tree-"));
  const app = join(temporary, "FieldNotes.app");
  try {
    await mkdir(join(app, "assets"), { recursive: true });
    await chmod(app, 0o755);
    await writeFile(join(app, "z.txt"), "z");
    await writeFile(join(app, "executable"), "launch");
    await writeFile(join(app, "assets", "a.txt"), "a");
    await chmod(join(app, "assets"), 0o755);
    await chmod(join(app, "z.txt"), 0o644);
    await chmod(join(app, "assets", "a.txt"), 0o600);
    await chmod(join(app, "executable"), 0o755);
    await symlink("executable", join(app, "executable-link"));

    const executable = await digestDirectoryTree(app);
    assert.equal(executable.fileCount, 3);
    assert.equal(executable.byteSize, 8);
    assert.equal(executable.treeDigestAlgorithm, "sha256-canonical-tree-v1");
    assert.match(executable.canonicalManifest, /^D 0755 0:\nD 0755 6:assets\n/u);
    assert.match(
      executable.canonicalManifest,
      /F 0755 10:executable 6 [a-f0-9]{64}\n/u,
    );
    assert.match(
      executable.canonicalManifest,
      /L [0-7]{4} 15:executable-link 10:executable\n/u,
    );
    assert.ok(
      executable.canonicalManifest.indexOf("6:assets") <
        executable.canonicalManifest.indexOf("10:executable"),
    );

    await chmod(join(app, "executable"), 0o644);
    const nonExecutable = await digestDirectoryTree(app);
    assert.notEqual(nonExecutable.treeSha256, executable.treeSha256);
    assert.match(
      nonExecutable.canonicalManifest,
      /F 0644 10:executable 6 [a-f0-9]{64}\n/u,
    );

    const future = new Date("2030-01-01T00:00:00.000Z");
    await utimes(join(app, "executable"), future, future);
    const timestampOnly = await digestDirectoryTree(app);
    assert.equal(timestampOnly.treeSha256, nonExecutable.treeSha256);

    await chmod(app, 0o700);
    const rootModeChanged = await digestDirectoryTree(app);
    assert.notEqual(rootModeChanged.treeSha256, timestampOnly.treeSha256);
    assert.match(rootModeChanged.canonicalManifest, /^D 0700 0:\n/u);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});

test("a symlink cannot stand in for the directory bundle root", async () => {
  const temporary = await mkdtemp(join(tmpdir(), "field-notes-tree-root-"));
  const archive = join(temporary, "FieldNotes.xcarchive");
  const alias = join(temporary, "archive-alias.xcarchive");
  try {
    await mkdir(archive);
    await writeFile(join(archive, "Info.plist"), "fixture");
    await symlink(archive, alias);
    await assert.rejects(
      digestDirectoryTree(alias),
      /root must be a non-symlink directory/u,
    );
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
