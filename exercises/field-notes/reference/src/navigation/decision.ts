import type { NavigationDecision, NavigationIntent } from "@field-notes/shared";

export async function resolveNavigationIntent(
  intent: NavigationIntent,
  recordExists: (recordId: string) => Promise<boolean>,
): Promise<NavigationDecision> {
  switch (intent.kind) {
    case "invalid":
      return {
        kind: "invalid",
        reason: intent.reason,
        fallbackHref: "/records",
      };
    case "records":
      return { kind: "navigate", href: "/records" };
    case "open-sync":
      return { kind: "navigate", href: "/sync" };
    case "open-settings":
      return { kind: "navigate", href: "/settings" };
    case "open-record": {
      if (!(await recordExists(intent.recordId))) {
        return {
          kind: "missing-record",
          recordId: intent.recordId,
          fallbackHref: "/records",
        };
      }
      const suffix = intent.destination === "edit" ? "/edit" : "";
      return {
        kind: "navigate",
        href: `/records/${encodeURIComponent(intent.recordId)}${suffix}`,
      };
    }
  }
}

export class RecentIntentSet {
  private readonly keys = new Set<string>();

  public constructor(private readonly capacity = 32) {}

  public accept(key: string): boolean {
    if (this.keys.has(key)) {
      return false;
    }
    this.keys.add(key);
    if (this.keys.size > this.capacity) {
      const oldest = this.keys.values().next().value as string | undefined;
      if (oldest !== undefined) {
        this.keys.delete(oldest);
      }
    }
    return true;
  }

  public has(key: string): boolean {
    return this.keys.has(key);
  }

  public forget(key: string): void {
    this.keys.delete(key);
  }
}

/** Keeps at most one latest warm input while startup state is not ready. */
export class LatestStartupIntentBuffer {
  private latest: NavigationIntent | null = null;

  public offer(intent: NavigationIntent): void {
    this.latest = intent;
  }

  public take(): NavigationIntent | null {
    const intent = this.latest;
    this.latest = null;
    return intent;
  }
}

export class StartupIntentCoordinator {
  public constructor(
    private readonly dependencies: {
      ready(): Promise<void>;
      recordExists(recordId: string): Promise<boolean>;
    },
    private readonly recent: {
      accept(key: string): boolean;
      forget?(key: string): void;
    } = new RecentIntentSet(),
  ) {}

  public async handle(
    intent: NavigationIntent,
    key: string,
  ): Promise<NavigationDecision> {
    if (!this.recent.accept(key)) {
      return { kind: "duplicate" };
    }
    try {
      await this.dependencies.ready();
      return await resolveNavigationIntent(intent, this.dependencies.recordExists);
    } catch (error) {
      this.recent.forget?.(key);
      throw error;
    }
  }

  public release(key: string): void {
    this.recent.forget?.(key);
  }
}
