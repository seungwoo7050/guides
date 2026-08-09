/**
 * Serializes file ownership, durable media completion, and reconciliation.
 * AppState can become active while a picker promise is still completing; the
 * shared queue prevents reconciliation from classifying that new owned file as
 * an orphan before its attachment transaction commits.
 */
export class SerializedForegroundPipeline {
  private tail: Promise<void> = Promise.resolve();

  public async run<Value>(operation: () => Promise<Value>): Promise<Value> {
    const preceding = this.tail;
    let release: (() => void) | undefined;
    this.tail = new Promise<void>((resolve) => {
      release = resolve;
    });
    await preceding;
    try {
      return await operation();
    } finally {
      release?.();
    }
  }
}
