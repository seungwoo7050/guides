import type { NavigationIntent } from "@field-notes/shared";
import type { NotificationNavigationIntent } from "@field-notes/lifecycle-engine";
import { RecentIntentSet } from "./decision";
import { intentKey } from "./stage01";

export function notificationRouteKey(intent: NotificationNavigationIntent): string {
  if (intent.kind === "open-record") {
    return intentKey({
      kind: "open-record",
      recordId: intent.recordId,
      destination: "detail",
      source: "notification",
    });
  }
  if (intent.kind === "open-sync") return "sync";
  return "records";
}

export type RouteReservation = {
  commit(): void;
  release(): void;
};

export function applyReservedRoute(
  reservation: RouteReservation,
  apply: () => void,
): void {
  try {
    apply();
    reservation.commit();
  } catch (error) {
    reservation.release();
    throw error;
  }
}

/** One bounded in-process route gate shared by link and notification owners. */
export class CrossSourceRouteArbiter {
  private readonly recent: RecentIntentSet;
  private readonly pending = new Set<string>();

  public constructor(capacity = 32) {
    this.recent = new RecentIntentSet(capacity);
  }

  public reserve(key: string): RouteReservation | null {
    if (this.pending.has(key) || this.recent.has(key)) return null;
    this.pending.add(key);
    let settled = false;
    return {
      commit: () => {
        if (settled) return;
        settled = true;
        this.pending.delete(key);
        this.recent.accept(key);
      },
      release: () => {
        if (settled) return;
        settled = true;
        this.pending.delete(key);
      },
    };
  }

  public reserveLink(intent: NavigationIntent): RouteReservation | null {
    return this.reserve(intentKey(intent));
  }

  public reserveNotification(
    intent: NotificationNavigationIntent,
  ): RouteReservation | null {
    return this.reserve(notificationRouteKey(intent));
  }
}
