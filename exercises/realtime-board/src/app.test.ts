import { afterEach, describe, expect, it } from "vitest";
import type { RawData, WebSocket } from "ws";

import { buildApp } from "./app";

function next(socket: WebSocket, type: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`timeout waiting for ${type}`)), 1_000);
    const handler = (raw: RawData) => {
      const message = JSON.parse(String(raw));
      if (message.type !== type) return;
      clearTimeout(timer);
      socket.off("message", handler);
      resolve(message);
    };
    socket.on("message", handler);
  });
}

function closed(socket: WebSocket): Promise<number> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("close timeout")), 1_000);
    socket.once("close", (code) => {
      clearTimeout(timer);
      resolve(code);
    });
  });
}

describe("realtime board protocol", () => {
  let app: Awaited<ReturnType<typeof buildApp>> | undefined;
  afterEach(async () => {
    await app?.close();
  });

  it("broadcasts one persistent sequence and restores a gap with a snapshot", async () => {
    app = await buildApp();
    await app.ready();
    const first = await app.injectWS("/ws") as WebSocket;
    const second = await app.injectWS("/ws") as WebSocket;

    for (const socket of [first, second]) {
      const snapshot = next(socket, "board.snapshot");
      socket.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
      expect((await snapshot).snapshot.boardId).toBe("planning");
    }

    const firstPatch = next(first, "board.patch");
    const secondPatch = next(second, "board.patch");
    first.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "review",
      x: 100,
      y: 120
    }));
    expect((await firstPatch).patch).toEqual((await secondPatch).patch);

    const recovered = next(second, "board.snapshot");
    second.send(JSON.stringify({ type: "snapshot.request", boardId: "planning", afterSequence: 0 }));
    expect((await recovered).snapshot).toMatchObject({ sequence: 1, items: [{ content: "review" }] });
  });

  it("closes a viewer that attempts a persistent write", async () => {
    app = await buildApp({
      resolveRole: (request) => request.headers["x-role"] === "viewer" ? "viewer" : "editor"
    });
    await app.ready();
    const viewer = await app.injectWS("/ws", { headers: { "x-role": "viewer" } }) as WebSocket;
    const joined = next(viewer, "board.snapshot");
    viewer.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
    await joined;

    const closeCode = closed(viewer);
    viewer.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "forbidden",
      x: 0,
      y: 0
    }));
    expect(await closeCode).toBe(1008);
  });

  it("rejects malformed input and use before join", async () => {
    app = await buildApp();
    await app.ready();
    const malformed = await app.injectWS("/ws") as WebSocket;
    const malformedClose = closed(malformed);
    malformed.send("{");
    expect(await malformedClose).toBe(1008);

    const unjoined = await app.injectWS("/ws") as WebSocket;
    const unjoinedClose = closed(unjoined);
    unjoined.send(JSON.stringify({ type: "snapshot.request", boardId: "planning" }));
    expect(await unjoinedClose).toBe(1008);
  });
});
