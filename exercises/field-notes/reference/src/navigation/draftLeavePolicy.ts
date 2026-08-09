import { decideDraftBack } from "./stage01";

export class OneShotNavigationPermit {
  private granted = false;

  public grant(): void {
    this.granted = true;
  }

  public consume(): boolean {
    const granted = this.granted;
    this.granted = false;
    return granted;
  }

  public revoke(): void {
    this.granted = false;
  }
}

export function handlePreventedDraftNavigation(
  permit: OneShotNavigationPermit,
  confirmDiscard: (discard: () => void) => void,
  dispatch: () => void,
): "bypassed" | "confirmation-requested" {
  if (permit.consume()) {
    dispatch();
    return "bypassed";
  }
  confirmDiscard(() => {
    permit.grant();
    try {
      dispatch();
    } finally {
      permit.revoke();
    }
  });
  return "confirmation-requested";
}

export function requestDraftLeave(
  dirty: boolean,
  confirmDiscard: (discard: () => void) => void,
  leave: () => void,
): "left" | "confirmation-requested" {
  if (decideDraftBack(dirty) === "leave") {
    leave();
    return "left";
  }
  confirmDiscard(leave);
  return "confirmation-requested";
}
