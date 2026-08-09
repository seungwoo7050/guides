import { afterEach, describe, expect, it } from "vitest";
import type { RawData, WebSocket } from "ws";
import { buildApp } from "./app";

function next(socket: WebSocket, type: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), 1_000);
    const handler = (raw: RawData) => {
      const message = JSON.parse(String(raw));
      if (message.type === type) {
        clearTimeout(timer);
        socket.off("message", handler);
        resolve(message);
      }
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

describe("실시간 보드", () => {
  let app: Awaited<ReturnType<typeof buildApp>> | undefined;
  const sockets: WebSocket[] = [];
  afterEach(async () => app?.close());

  it("broadcasts the same persistent patch and recovers a sequence gap with a snapshot", async () => {
    app = await buildApp();
    await app.ready();
    const first = await app.injectWS("/ws") as WebSocket;
    const second = await app.injectWS("/ws") as WebSocket;
    sockets.push(first, second);
    for (const socket of sockets) {
      const snapshot = next(socket, "board.snapshot");
      socket.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
      expect((await snapshot).snapshot.boardId).toBe("planning");
    }
    const firstPatch = next(first, "board.patch");
    const secondPatch = next(second, "board.patch");
    first.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "검토할 항목",
      x: 100,
      y: 120
    }));
    const [observedFirst, observedSecond] = await Promise.all([firstPatch, secondPatch]);
    expect(observedFirst.patch).toEqual(observedSecond.patch);
    const nextFirstPatch = next(first, "board.patch");
    const nextSecondPatch = next(second, "board.patch");
    second.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "두 번째 항목",
      x: 200,
      y: 220
    }));
    await Promise.all([nextFirstPatch, nextSecondPatch]);
    const recovered = next(second, "board.snapshot");
    second.send(JSON.stringify({ type: "snapshot.request", boardId: "planning", afterSequence: 1 }));
    expect((await recovered).snapshot).toMatchObject({
      sequence: 2,
      items: [{ content: "검토할 항목" }, { content: "두 번째 항목" }]
    });
  });

  it("rejects a stale baseVersion without mutating the board", async () => {
    app = await buildApp();
    await app.ready();
    const socket = await app.injectWS("/ws") as WebSocket;
    sockets.push(socket);
    const joined = next(socket, "board.snapshot");
    socket.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
    await joined;
    const created = next(socket, "board.patch");
    socket.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "original",
      x: 10,
      y: 20
    }));
    await created;
    const current = next(socket, "board.snapshot");
    socket.send(JSON.stringify({ type: "snapshot.request", boardId: "planning" }));
    const item = (await current).snapshot.items[0];

    const updated = next(socket, "board.patch");
    socket.send(JSON.stringify({
      type: "item.update",
      boardId: "planning",
      itemId: item.id,
      content: "current",
      baseVersion: item.version
    }));
    await updated;

    const rejected = next(socket, "board.snapshot");
    socket.send(JSON.stringify({
      type: "item.update",
      boardId: "planning",
      itemId: item.id,
      content: "stale write",
      baseVersion: item.version
    }));
    expect((await rejected).snapshot.items[0]).toMatchObject({ content: "current", version: 2 });
  });

  it("keeps move previews ephemeral and persists only a valid final move", async () => {
    app = await buildApp();
    await app.ready();
    const socket = await app.injectWS("/ws") as WebSocket;
    const observer = await app.injectWS("/ws") as WebSocket;
    sockets.push(socket, observer);
    for (const client of [socket, observer]) {
      const joined = next(client, "board.snapshot");
      client.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
      await joined;
    }
    const created = next(socket, "board.patch");
    const observedCreate = next(observer, "board.patch");
    socket.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "move me",
      x: 10,
      y: 20
    }));
    await Promise.all([created, observedCreate]);
    const initialSnapshot = next(socket, "board.snapshot");
    socket.send(JSON.stringify({ type: "snapshot.request", boardId: "planning" }));
    const item = (await initialSnapshot).snapshot.items[0];

    const preview = next(observer, "item.preview");
    socket.send(JSON.stringify({
      type: "item.move",
      boardId: "planning",
      itemId: item.id,
      x: 999,
      y: 888,
      baseVersion: item.version,
      final: false
    }));
    expect((await preview).preview).toEqual({
      boardId: "planning",
      itemId: item.id,
      x: 999,
      y: 888,
      baseVersion: item.version
    });
    const afterPreview = next(observer, "board.snapshot");
    observer.send(JSON.stringify({ type: "snapshot.request", boardId: "planning" }));
    expect((await afterPreview).snapshot).toMatchObject({
      sequence: 1,
      items: [{ x: 10, y: 20, version: 1 }]
    });

    const finalPatch = next(socket, "board.patch");
    const observedFinalPatch = next(observer, "board.patch");
    socket.send(JSON.stringify({
      type: "item.move",
      boardId: "planning",
      itemId: item.id,
      x: 300,
      y: 240,
      baseVersion: item.version,
      final: true
    }));
    expect((await finalPatch).patch.sequence).toBe(2);
    expect((await observedFinalPatch).patch.sequence).toBe(2);
    const afterFinal = next(socket, "board.snapshot");
    socket.send(JSON.stringify({ type: "snapshot.request", boardId: "planning" }));
    expect((await afterFinal).snapshot.items[0]).toMatchObject({ x: 300, y: 240, version: 2 });

    const stale = next(socket, "board.snapshot");
    socket.send(JSON.stringify({
      type: "item.move",
      boardId: "planning",
      itemId: item.id,
      x: 0,
      y: 0,
      baseVersion: item.version,
      final: true
    }));
    expect((await stale).snapshot.items[0]).toMatchObject({ x: 300, y: 240, version: 2 });
  });

  it("closes a viewer that attempts a persistent write", async () => {
    app = await buildApp((request) => request.headers["x-role"] === "viewer" ? "viewer" : "editor");
    await app.ready();
    const editor = await app.injectWS("/ws", { headers: { "x-role": "editor" } }) as WebSocket;
    const updateViewer = await app.injectWS("/ws", { headers: { "x-role": "viewer" } }) as WebSocket;
    const moveViewer = await app.injectWS("/ws", { headers: { "x-role": "viewer" } }) as WebSocket;
    sockets.push(editor, updateViewer, moveViewer);
    for (const socket of [editor, updateViewer, moveViewer]) {
      const joined = next(socket, "board.snapshot");
      socket.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
      await joined;
    }
    const editorPatch = next(editor, "board.patch");
    const updateViewerPatch = next(updateViewer, "board.patch");
    const moveViewerPatch = next(moveViewer, "board.patch");
    editor.send(JSON.stringify({
      type: "item.create",
      boardId: "planning",
      content: "existing",
      x: 10,
      y: 20
    }));
    await Promise.all([editorPatch, updateViewerPatch, moveViewerPatch]);
    const updateSnapshot = next(updateViewer, "board.snapshot");
    updateViewer.send(JSON.stringify({ type: "snapshot.request", boardId: "planning" }));
    const item = (await updateSnapshot).snapshot.items[0];

    const updateCloseCode = closed(updateViewer);
    updateViewer.send(JSON.stringify({
      type: "item.update",
      boardId: "planning",
      itemId: item.id,
      content: "forbidden",
      baseVersion: item.version
    }));
    expect(await updateCloseCode).toBe(1008);

    const moveCloseCode = closed(moveViewer);
    moveViewer.send(JSON.stringify({
      type: "item.move",
      boardId: "planning",
      itemId: item.id,
      x: 40,
      y: 50,
      baseVersion: item.version,
      final: true
    }));
    expect(await moveCloseCode).toBe(1008);
  });
});
