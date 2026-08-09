import type {
  Attachment,
  AttachmentFileStore,
  AttachmentRepository,
  IdGenerator,
} from "@field-notes/shared";
import * as FileSystem from "expo-file-system/legacy";
import { productionIds } from "./productionIdentity";

export class AppOwnedAttachmentService {
  public constructor(
    private readonly repository: AttachmentRepository,
    private readonly files: AttachmentFileStore,
    private readonly ids: IdGenerator = productionIds,
  ) {}

  public async attachNonSensitiveTestFile(recordId: string): Promise<Attachment> {
    if (FileSystem.cacheDirectory == null) {
      throw new Error("cache directory is unavailable");
    }
    const attachmentId = this.ids.attachmentId();
    const temporaryUri = `${FileSystem.cacheDirectory}${attachmentId}.txt`;
    await FileSystem.writeAsStringAsync(
      temporaryUri,
      `Field Notes non-sensitive Stage 02 fixture for ${recordId}\n`,
    );
    try {
      const owned = await this.files.takeOwnership(temporaryUri);
      return await this.repository.attachOwnedFile({
        id: attachmentId,
        recordId,
        localUri: owned.ownedUri,
        checksum: owned.checksum,
        byteSize: owned.byteSize,
        mimeType: "text/plain",
      });
    } finally {
      await FileSystem.deleteAsync(temporaryUri, { idempotent: true }).catch(
        () => undefined,
      );
    }
  }
}
