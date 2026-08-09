import type { AttachmentFileStore, IdGenerator } from "@field-notes/shared";
import {
  assertAppOwnedFileUri,
  assertFlatGeneratedIdentity,
  ownedFileName,
} from "../ownedFileInvariant";
import { sequentialIds } from "./DeterministicLocalStore";

const OWNED_DIRECTORY = "file://field-notes/owned/";

export class DeterministicFileStore implements AttachmentFileStore {
  private readonly temporary = new Map<string, string>();
  private readonly staging = new Map<string, string>();
  private readonly owned = new Map<string, string>();
  private copyPartialFault = false;

  public constructor(private readonly ids: IdGenerator = sequentialIds()) {}

  public addTemporary(uri: string, contents: string): void {
    this.temporary.set(uri, contents);
  }

  public failNextCopyPartially(): void {
    this.copyPartialFault = true;
  }

  public addOrphan(uri: string, contents = "orphan"): void {
    this.owned.set(uri, contents);
  }

  public removeOutsideTheAppForTest(uri: string): void {
    this.owned.delete(uri);
  }

  public ownedUris(): string[] {
    return [...this.owned.keys()].sort();
  }

  public async takeOwnership(temporaryUri: string): Promise<{
    ownedUri: string;
    checksum: string;
    byteSize: number;
  }> {
    const contents = this.temporary.get(temporaryUri);
    if (contents === undefined) throw new Error("temporary file is missing");
    const id = this.ids.attachmentId();
    assertFlatGeneratedIdentity(id);
    const stagingUri = `file://field-notes/staging/${id}.partial`;
    this.staging.set(stagingUri, contents.slice(0, Math.max(1, contents.length / 2)));
    if (this.copyPartialFault) {
      this.copyPartialFault = false;
      throw new Error("injected partial copy");
    }
    if (contents.length === 0) throw new Error("zero-byte file");
    const ownedUri = `${OWNED_DIRECTORY}${ownedFileName(id)}`;
    this.staging.delete(stagingUri);
    this.owned.set(ownedUri, contents);
    return {
      ownedUri,
      checksum: `deterministic-${contents.length}-${contents.charCodeAt(0)}`,
      byteSize: contents.length,
    };
  }

  public async remove(ownedUri: string): Promise<void> {
    assertAppOwnedFileUri(OWNED_DIRECTORY, ownedUri);
    this.owned.delete(ownedUri);
  }

  public async listOrphans(): Promise<string[]> {
    return this.ownedUris();
  }

  public async exists(ownedUri: string): Promise<boolean> {
    return this.owned.has(ownedUri);
  }

  public async cleanupStaging(): Promise<number> {
    const count = this.staging.size;
    this.staging.clear();
    return count;
  }
}
