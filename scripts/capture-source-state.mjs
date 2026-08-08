import { createHash } from "node:crypto";
import { lstat, readFile, readlink } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";

const hash = createHash("sha256");
const index = git(["ls-files", "--stage", "-z"]);
const paths = git(["ls-files", "--cached", "--others", "--exclude-standard", "-z"])
  .toString("utf8")
  .split("\0")
  .filter(Boolean)
  .filter((relative) => path.basename(relative) !== "next-env.d.ts")
  .sort();

hash.update("index\0");
hash.update(index);

for (const relative of paths) {
  hash.update("path\0");
  hash.update(relative);
  hash.update("\0");

  let metadata;
  try {
    metadata = await lstat(relative);
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
    hash.update("missing\0");
    continue;
  }

  hash.update(`${metadata.mode & 0o7777}\0`);
  if (metadata.isSymbolicLink()) {
    hash.update("symlink\0");
    hash.update(await readlink(relative));
  } else if (metadata.isFile()) {
    hash.update("file\0");
    hash.update(await readFile(relative));
  } else if (metadata.isDirectory()) {
    hash.update("directory\0");
  } else {
    hash.update("other\0");
  }
}

process.stdout.write(`${hash.digest("hex")}\n`);

function git(args) {
  const result = spawnSync("git", args, { encoding: "buffer", maxBuffer: 64 * 1024 * 1024 });
  if (result.status !== 0) {
    throw new Error(`git ${args.join(" ")} 실패\n${result.stderr.toString("utf8")}`);
  }
  return result.stdout;
}
