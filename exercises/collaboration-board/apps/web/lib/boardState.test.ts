import { describe, expect, it } from "vitest";

import type { BoardSnapshot, ServerEvent } from "@board/contracts";
import { reduceBoardEvent } from "./boardState";

const snapshot: BoardSnapshot = {
  boardId: "00000000-0000-4000-8000-000000000001",
  title: "Board",
  version: 1,
  sequence: 1,
  closed: false,
  role: "editor",
  items: [{
    id: "00000000-0000-4000-8000-000000000002",
    boardId: "00000000-0000-4000-8000-000000000001",
    kind: "note",
    content: "one",
    x: 10,
    y: 20,
    width: 240,
    height: 140,
    version: 1
  }],
  serverTime: new Date(0).toISOString()
};

describe("reduceBoardEvent", () => {
  it("applies a preview without advancing durable sequence", () => {
    const event: ServerEvent = {
      type: "board.patch",
      patch: {
        boardId: snapshot.boardId,
        sequence: 20,
        version: snapshot.version,
        operation: "item.move",
        actorId: "00000000-0000-4000-8000-000000000003",
        item: { ...snapshot.items[0]!, x: 400, y: 300 },
        final: false
      }
    };
    expect(reduceBoardEvent(snapshot, event).snapshot).toMatchObject({
      sequence: 1,
      items: [{ x: 400, y: 300 }]
    });
  });

  it("requests a snapshot when a durable sequence is skipped", () => {
    const event: ServerEvent = {
      type: "board.patch",
      patch: {
        boardId: snapshot.boardId,
        sequence: 3,
        version: 2,
        operation: "item.update",
        actorId: "00000000-0000-4000-8000-000000000003",
        item: { ...snapshot.items[0]!, content: "gap", version: 2 },
        final: true
      }
    };
    expect(reduceBoardEvent(snapshot, event)).toMatchObject({ needsSnapshot: true, snapshot: { sequence: 1 } });
  });
});
