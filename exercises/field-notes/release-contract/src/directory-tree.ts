import { createHash } from "node:crypto";
import { isUtf8 } from "node:buffer";
import { constants, type Stats } from "node:fs";
import { lstat, open, readdir, readlink } from "node:fs/promises";
import { join, resolve } from "node:path";

export const DIRECTORY_TREE_DIGEST_ALGORITHM =
  "sha256-canonical-tree-v1" as const;

type DirectoryEntry = {
  type: "directory";
  path: string;
  mode: string;
};

type FileEntry = {
  type: "file";
  path: string;
  mode: string;
  byteSize: number;
  sha256: string;
};

type SymlinkEntry = {
  type: "symlink";
  path: string;
  mode: string;
  target: string;
};

type TreeEntry = DirectoryEntry | FileEntry | SymlinkEntry;

export type DirectoryTreeDigest = {
  fileCount: number;
  byteSize: number;
  treeSha256: string;
  treeDigestAlgorithm: typeof DIRECTORY_TREE_DIGEST_ALGORITHM;
  canonicalManifest: string;
};

function permissionMode(stats: Stats): string {
  return (stats.mode & 0o7777).toString(8).padStart(4, "0");
}

function lengthPrefixed(value: string): string {
  return `${Buffer.byteLength(value, "utf8")}:${value}`;
}

function record(entry: TreeEntry): string {
  const path = lengthPrefixed(entry.path);
  switch (entry.type) {
    case "directory":
      return `D ${entry.mode} ${path}\n`;
    case "file":
      return `F ${entry.mode} ${path} ${entry.byteSize} ${entry.sha256}\n`;
    case "symlink":
      return `L ${entry.mode} ${path} ${lengthPrefixed(entry.target)}\n`;
  }
}

function sameFileObservation(left: Stats, right: Stats): boolean {
  return (
    left.dev === right.dev &&
    left.ino === right.ino &&
    left.size === right.size &&
    left.mode === right.mode &&
    left.mtimeMs === right.mtimeMs
  );
}

async function hashRegularFile(
  path: string,
  observed: Stats,
): Promise<{ byteSize: number; mode: string; sha256: string }> {
  const descriptor = await open(
    path,
    constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0),
  );
  try {
    const before = await descriptor.stat();
    if (!before.isFile() || !sameFileObservation(observed, before)) {
      throw new Error(`directory tree entry changed before read: ${path}`);
    }
    const digest = createHash("sha256");
    const buffer = Buffer.allocUnsafe(1024 * 1024);
    let position = 0;
    while (true) {
      const { bytesRead } = await descriptor.read(
        buffer,
        0,
        buffer.length,
        position,
      );
      if (bytesRead === 0) break;
      digest.update(buffer.subarray(0, bytesRead));
      position += bytesRead;
    }
    const after = await descriptor.stat();
    if (position !== before.size || !sameFileObservation(before, after)) {
      throw new Error(`directory tree entry changed during read: ${path}`);
    }
    const currentPath = await lstat(path);
    if (!sameFileObservation(after, currentPath)) {
      throw new Error(`directory tree path changed after read: ${path}`);
    }
    return {
      byteSize: before.size,
      mode: permissionMode(before),
      sha256: digest.digest("hex"),
    };
  } finally {
    await descriptor.close();
  }
}

function decodeUtf8(value: Buffer, label: string): string {
  if (!isUtf8(value)) {
    throw new Error(`directory tree ${label} is not valid UTF-8`);
  }
  return value.toString("utf8");
}

async function walk(
  absoluteDirectory: string,
  relativeDirectory: string,
  entries: TreeEntry[],
  observed: Stats,
): Promise<void> {
  const before = await lstat(absoluteDirectory);
  if (!before.isDirectory() || !sameFileObservation(observed, before)) {
    throw new Error(
      `directory tree directory changed before traversal: ${absoluteDirectory}`,
    );
  }
  const names = await readdir(absoluteDirectory, { encoding: "buffer" });
  for (const rawName of names) {
    const name = decodeUtf8(rawName, "path");
    const absolutePath = join(absoluteDirectory, name);
    const relativePath = relativeDirectory
      ? `${relativeDirectory}/${name}`
      : name;
    const metadata = await lstat(absolutePath);
    if (metadata.isDirectory()) {
      entries.push({
        type: "directory",
        path: relativePath,
        mode: permissionMode(metadata),
      });
      await walk(absolutePath, relativePath, entries, metadata);
      continue;
    }
    if (metadata.isFile()) {
      const file = await hashRegularFile(absolutePath, metadata);
      entries.push({ type: "file", path: relativePath, ...file });
      continue;
    }
    if (metadata.isSymbolicLink()) {
      const rawTarget = await readlink(absolutePath, { encoding: "buffer" });
      const after = await lstat(absolutePath);
      if (!after.isSymbolicLink() || !sameFileObservation(metadata, after)) {
        throw new Error(
          `directory tree symlink changed during read: ${absolutePath}`,
        );
      }
      entries.push({
        type: "symlink",
        path: relativePath,
        mode: permissionMode(metadata),
        target: decodeUtf8(rawTarget, "symlink target"),
      });
      continue;
    }
    throw new Error(`directory tree special file is unsupported: ${absolutePath}`);
  }
  const after = await lstat(absoluteDirectory);
  if (!after.isDirectory() || !sameFileObservation(before, after)) {
    throw new Error(
      `directory tree directory changed during traversal: ${absoluteDirectory}`,
    );
  }
}

export async function digestDirectoryTree(
  root: string,
): Promise<DirectoryTreeDigest> {
  const absoluteRoot = resolve(root);
  const rootMetadata = await lstat(absoluteRoot);
  if (rootMetadata.isSymbolicLink() || !rootMetadata.isDirectory()) {
    throw new Error(`directory tree root must be a non-symlink directory: ${root}`);
  }

  const entries: TreeEntry[] = [
    { type: "directory", path: "", mode: permissionMode(rootMetadata) },
  ];
  await walk(absoluteRoot, "", entries, rootMetadata);
  entries.sort((left, right) =>
    Buffer.compare(Buffer.from(left.path, "utf8"), Buffer.from(right.path, "utf8")),
  );
  const canonicalManifest = entries.map(record).join("");
  const files = entries.filter((entry): entry is FileEntry => entry.type === "file");
  return {
    fileCount: files.length,
    byteSize: files.reduce((total, entry) => total + entry.byteSize, 0),
    treeSha256: createHash("sha256")
      .update(canonicalManifest, "utf8")
      .digest("hex"),
    treeDigestAlgorithm: DIRECTORY_TREE_DIGEST_ALGORITHM,
    canonicalManifest,
  };
}
