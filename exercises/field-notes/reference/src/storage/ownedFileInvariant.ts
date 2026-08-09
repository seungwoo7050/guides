const FLAT_IDENTITY = /^[A-Za-z0-9_-]+$/;

export function assertFlatGeneratedIdentity(identity: string): void {
  if (
    identity === "" ||
    identity === "." ||
    identity === ".." ||
    !FLAT_IDENTITY.test(identity)
  ) {
    throw new Error("generated file identity must be one safe path segment");
  }
}

export function ownedFileName(identity: string): string {
  assertFlatGeneratedIdentity(identity);
  return `${identity}.bin`;
}

export function assertAppOwnedFileUri(
  ownedDirectory: string,
  candidateUri: string,
): void {
  if (!ownedDirectory.endsWith("/") || !candidateUri.startsWith(ownedDirectory)) {
    throw new Error("refusing to mutate a file outside the app-owned directory");
  }
  const encodedSuffix = candidateUri.slice(ownedDirectory.length);
  if (
    encodedSuffix === "" ||
    encodedSuffix.includes("?") ||
    encodedSuffix.includes("#")
  ) {
    throw new Error("app-owned file URI must name one generated file");
  }
  let suffix: string;
  try {
    suffix = decodeURIComponent(encodedSuffix);
  } catch {
    throw new Error("app-owned file URI has invalid percent encoding");
  }
  if (
    suffix !== encodedSuffix ||
    suffix === "." ||
    suffix === ".." ||
    suffix.includes("/") ||
    suffix.includes("\\") ||
    !/^[A-Za-z0-9_-]+\.bin$/.test(suffix)
  ) {
    throw new Error("app-owned file URI must name one generated file");
  }
}
