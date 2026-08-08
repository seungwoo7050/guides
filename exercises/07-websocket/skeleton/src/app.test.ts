import { afterEach, describe, expect, it } from "vitest";
import type { WebSocket } from "ws";
import { buildApp } from "./app";

function next(socket: WebSocket, type: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timeout")), 1_000);
    const handler = (raw: unknown) => {
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

describe("실시간 보드", () => {
  let app: Awaited<ReturnType<typeof buildApp>> | undefined;
  afterEach(async () => app?.close());
  it("재연결 요청에 스냅숏을 반환합니다", async () => {
    app = await buildApp();
    await app.ready();
    const socket = await app.injectWS("/ws") as WebSocket;
    socket.send(JSON.stringify({ type: "board.join", boardId: "planning" }));
    expect((await next(socket, "board.snapshot")).snapshot.boardId).toBe("planning");
    socket.terminate();
  });
});
