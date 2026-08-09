import type { AttachmentFileStore, IdGenerator } from "@field-notes/shared";
import * as FileSystem from "expo-file-system/legacy";
import {
  assertAppOwnedFileUri,
  assertFlatGeneratedIdentity,
  ownedFileName,
} from "./ownedFileInvariant";
import { productionIds } from "./productionIdentity";

export type ExpoAttachmentFileStoreOptions = {
  ids?: IdGenerator;
  documentDirectory?: string;
};

export class ExpoAttachmentFileStore implements AttachmentFileStore {
  private readonly stagingDirectory: string;
  private readonly ownedDirectory: string;
  private readonly ids: IdGenerator;

  public constructor(options: ExpoAttachmentFileStoreOptions = {}) {
    const documentDirectory =
      options.documentDirectory ?? FileSystem.documentDirectory;
    if (documentDirectory == null) {
      throw new Error("app document directory is unavailable");
    }
    const root = `${documentDirectory}field-notes/`;
    this.stagingDirectory = `${root}staging/`;
    this.ownedDirectory = `${root}owned/`;
    this.ids = options.ids ?? productionIds;
  }

  private async ensureDirectories(): Promise<void> {
    await FileSystem.makeDirectoryAsync(this.stagingDirectory, {
      intermediates: true,
    });
    await FileSystem.makeDirectoryAsync(this.ownedDirectory, {
      intermediates: true,
    });
  }

  public async takeOwnership(temporaryUri: string): Promise<{
    ownedUri: string;
    checksum: string;
    byteSize: number;
  }> {
    await this.ensureDirectories();
    const identity = this.ids.attachmentId();
    assertFlatGeneratedIdentity(identity);
    const stagingUri = `${this.stagingDirectory}${identity}.partial`;
    const ownedUri = `${this.ownedDirectory}${ownedFileName(identity)}`;
    try {
      await FileSystem.copyAsync({ from: temporaryUri, to: stagingUri });
      const info = await FileSystem.getInfoAsync(stagingUri, { md5: true });
      if (
        !info.exists ||
        info.isDirectory ||
        info.size <= 0 ||
        info.md5 === undefined
      ) {
        throw new Error("copied file is missing, empty, or has no checksum");
      }
      await FileSystem.moveAsync({ from: stagingUri, to: ownedUri });
      return { ownedUri, checksum: info.md5, byteSize: info.size };
    } catch (error) {
      await FileSystem.deleteAsync(stagingUri, { idempotent: true }).catch(
        () => undefined,
      );
      throw error;
    }
  }

  private assertOwnedUri(uri: string): void {
    assertAppOwnedFileUri(this.ownedDirectory, uri);
  }

  public async remove(ownedUri: string): Promise<void> {
    this.assertOwnedUri(ownedUri);
    await FileSystem.deleteAsync(ownedUri, { idempotent: true });
  }

  public async exists(ownedUri: string): Promise<boolean> {
    this.assertOwnedUri(ownedUri);
    const info = await FileSystem.getInfoAsync(ownedUri);
    return info.exists && !info.isDirectory;
  }

  public async listOrphans(): Promise<string[]> {
    await this.ensureDirectories();
    const names = await FileSystem.readDirectoryAsync(this.ownedDirectory);
    return names.map((name) => `${this.ownedDirectory}${name}`).sort();
  }

  public async cleanupStaging(): Promise<number> {
    await this.ensureDirectories();
    const names = await FileSystem.readDirectoryAsync(this.stagingDirectory);
    let removed = 0;
    for (const name of names) {
      await FileSystem.deleteAsync(`${this.stagingDirectory}${name}`, {
        idempotent: true,
      });
      removed += 1;
    }
    return removed;
  }
}
