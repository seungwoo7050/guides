import type {
  AttachmentFileStore,
  AttachmentRepository,
  StorageMaintenance,
  StorageReconciliationReport,
} from "@field-notes/shared";

export class StorageReconciler implements StorageMaintenance {
  public constructor(
    private readonly attachments: AttachmentRepository,
    private readonly files: AttachmentFileStore,
  ) {}

  public async reconcile(): Promise<StorageReconciliationReport> {
    const report: StorageReconciliationReport = {
      removedOrphanUris: [],
      missingAttachmentIds: [],
      removedAttachmentIds: [],
      stagingFilesRemoved: 0,
      failures: [],
    };
    try {
      report.stagingFilesRemoved = await this.files.cleanupStaging();
    } catch (error) {
      report.failures.push({ resource: "staging", reason: String(error) });
    }

    const attachments = await this.attachments.listAttachments();
    for (const attachment of attachments) {
      if (attachment.state === "removed") continue;
      if (attachment.state === "cleanup-pending") {
        try {
          await this.files.remove(attachment.localUri);
          await this.attachments.markRemoved(attachment.id);
          report.removedAttachmentIds.push(attachment.id);
        } catch (error) {
          report.failures.push({
            resource: `attachment:${attachment.id}`,
            reason: String(error),
          });
        }
        continue;
      }
      try {
        if (!(await this.files.exists(attachment.localUri))) {
          await this.attachments.markMissing(attachment.id);
          report.missingAttachmentIds.push(attachment.id);
        }
      } catch (error) {
        report.failures.push({
          resource: `attachment:${attachment.id}`,
          reason: String(error),
        });
      }
    }

    const referenced = new Set(
      attachments
        .filter((attachment) => attachment.state !== "removed")
        .map((attachment) => attachment.localUri),
    );
    for (const uri of await this.files.listOrphans()) {
      if (referenced.has(uri)) continue;
      try {
        await this.files.remove(uri);
        report.removedOrphanUris.push(uri);
      } catch (error) {
        report.failures.push({ resource: uri, reason: String(error) });
      }
    }
    return report;
  }
}
