import { describe, expect, it } from "vitest";

import { BoardStore } from "./state";

describe("BoardStore", () => {
  it("keeps previews ephemeral and commits only a valid final move", () => {
    const store = new BoardStore();
    expect(store.createItem("planning", { content: "move me", x: 10, y: 20 })).toMatchObject({
      kind: "committed",
      event: { patch: { sequence: 1, boardVersion: 1, item: { content: "move me", version: 1 } } }
    });
    const item = store.snapshot("planning").items[0]!;

    expect(store.moveItem("planning", {
      itemId: item.id,
      x: 900,
      y: 800,
      baseVersion: item.version,
      final: false
    })).toMatchObject({ kind: "preview" });
    expect(store.snapshot("planning")).toMatchObject({
      sequence: 1,
      items: [{ x: 10, y: 20, version: 1 }]
    });

    expect(store.moveItem("planning", {
      itemId: item.id,
      x: 300,
      y: 240,
      baseVersion: item.version,
      final: true
    })).toMatchObject({
      kind: "committed",
      event: {
        patch: {
          sequence: 2,
          boardVersion: 2,
          item: { x: 300, y: 240, version: 2 }
        }
      }
    });
    expect(store.snapshot("planning").items[0]).toMatchObject({ x: 300, y: 240, version: 2 });
  });

  it("rejects positions outside the board coordinate space", () => {
    const store = new BoardStore();
    expect(() => store.createItem("planning", { content: "outside", x: -1, y: 0 })).toThrow(/coordinate space/);
    expect(() => store.createItem("planning", { content: "outside", x: 0, y: 901 })).toThrow(/coordinate space/);
    expect(store.snapshot("planning")).toMatchObject({ sequence: 0, items: [] });
  });

  it("returns a current snapshot for a stale write without mutation", () => {
    const store = new BoardStore();
    store.createItem("planning", { content: "original", x: 10, y: 20 });
    const item = store.snapshot("planning").items[0]!;
    store.updateItem("planning", { itemId: item.id, content: "current", baseVersion: item.version });

    expect(store.updateItem("planning", {
      itemId: item.id,
      content: "stale",
      baseVersion: item.version
    })).toMatchObject({
      kind: "stale",
      snapshot: { sequence: 2, items: [{ content: "current", version: 2 }] }
    });
  });
});
