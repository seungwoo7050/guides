import type { BoardSnapshot, ServerEvent } from "@board/contracts";

export interface BoardReduction {
  snapshot: BoardSnapshot | null;
  needsSnapshot: boolean;
  closedReason: string | null;
}

// [Implementation 9-3] Reduce snapshots, transient previews, durable patches, sequence gaps, and closure into one deterministic browser-state transition.
export function reduceBoardEvent(
  current: BoardSnapshot | null,
  event: ServerEvent
): BoardReduction {
  if (event.type === "board.snapshot") {
    return { snapshot: clone(event.snapshot), needsSnapshot: false, closedReason: null };
  }
  if (event.type === "board.closed") {
    return {
      snapshot: current ? { ...current, closed: true } : null,
      needsSnapshot: false,
      closedReason: event.reason
    };
  }
  if (event.type !== "board.patch" || event.patch.operation === "cursor" || !event.patch.item) {
    return { snapshot: current, needsSnapshot: false, closedReason: null };
  }
  if (!current || current.boardId !== event.patch.boardId) {
    return { snapshot: current, needsSnapshot: true, closedReason: null };
  }

  const durable = event.patch.final !== false;
  if (durable && event.patch.sequence !== current.sequence + 1) {
    return { snapshot: current, needsSnapshot: true, closedReason: null };
  }

  const items = upsertItem(current.items, event.patch.item);
  return {
    snapshot: {
      ...current,
      items,
      sequence: durable ? event.patch.sequence : current.sequence,
      version: durable ? event.patch.version : current.version
    },
    needsSnapshot: false,
    closedReason: null
  };
}

function upsertItem(
  items: BoardSnapshot["items"],
  item: BoardSnapshot["items"][number]
): BoardSnapshot["items"] {
  const index = items.findIndex((candidate) => candidate.id === item.id);
  if (index < 0) return [...items, { ...item }];
  return items.map((candidate, current) => current === index ? { ...item } : candidate);
}

function clone(snapshot: BoardSnapshot): BoardSnapshot {
  return { ...snapshot, items: snapshot.items.map((item) => ({ ...item })) };
}
