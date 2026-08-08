import { afterEach, describe, expect, it } from "vitest";
import { WebSocket, type RawData } from "ws";
import { createMemoryRepository } from "@board/db";
import { buildApp } from "./app";

function cookieOf(headers: Record<string, string | string[] | number | undefined>) {
  const value = headers["set-cookie"];
  return String(Array.isArray(value) ? value[0] : value).split(";")[0];
}
function next(socket: WebSocket, type: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`메시지 대기 시간이 끝났습니다: ${type}`)), 3_000);
    const handler = (raw: RawData) => {
      const message = JSON.parse(raw.toString());
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
    const timer = setTimeout(() => reject(new Error("WebSocket 종료 시간이 초과되었습니다.")), 3_000);
    socket.once("close", (code) => {
      clearTimeout(timer);
      resolve(code);
    });
  });
}

async function loginAndConnect(
  app: ReturnType<typeof buildApp>,
  handle: string,
  sockets: WebSocket[]
) {
  const login = await app.inject({
    method: "POST",
    url: "/auth/login",
    payload: { handle, displayName: `${handle} 사용자` }
  });
  const socket = await app.injectWS("/ws", {
    headers: { cookie: cookieOf(login.headers), origin: "http://localhost:3000" }
  }) as WebSocket;
  sockets.push(socket);
  return socket;
}

describe("WebSocket 보드 계약", () => {
  const sockets: WebSocket[] = [];
  afterEach(() => sockets.forEach((socket) => socket.terminate()));

  it("재접속한 구성원에게 최신 스냅숏을 보냅니다", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const owner = await repo.upsertUser({ handle: "owner", displayName: "보드 소유자" });
    const [board] = await repo.listBoards(owner.id);
    const app = buildApp(repo);
    await app.ready();
    const login = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { handle: "owner", displayName: "보드 소유자" }
    });
    const socket = await app.injectWS("/ws", {
      headers: { cookie: cookieOf(login.headers), origin: "http://localhost:3000" }
    }) as WebSocket;
    sockets.push(socket);
    const snapshot = next(socket, "board.snapshot");
    socket.send(JSON.stringify({ type: "board.join", boardId: board!.id }));
    expect((await snapshot).snapshot.boardId).toBe(board!.id);
    await app.close();
  });

  it("형식이 잘못된 메시지는 정책 위반으로 연결을 닫습니다", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const app = buildApp(repo);
    await app.ready();
    const socket = await loginAndConnect(app, "owner", sockets);
    const closeCode = closed(socket);
    socket.send("{}");
    expect(await closeCode).toBe(1008);
    await app.close();
  });

  it("한 편집자의 변경을 같은 보드의 다른 구성원에게 전달합니다", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const owner = await repo.upsertUser({ handle: "owner", displayName: "보드 소유자" });
    const [board] = await repo.listBoards(owner.id);
    const app = buildApp(repo);
    await app.ready();
    const ownerSocket = await loginAndConnect(app, "owner", sockets);
    const editorSocket = await loginAndConnect(app, "editor", sockets);

    const ownerSnapshot = next(ownerSocket, "board.snapshot");
    ownerSocket.send(JSON.stringify({ type: "board.join", boardId: board!.id }));
    await ownerSnapshot;
    const editorSnapshot = next(editorSocket, "board.snapshot");
    editorSocket.send(JSON.stringify({ type: "board.join", boardId: board!.id }));
    await editorSnapshot;

    const patch = next(editorSocket, "board.patch");
    ownerSocket.send(JSON.stringify({
      type: "item.create",
      boardId: board!.id,
      kind: "note",
      content: "공유할 변경",
      x: 80,
      y: 60
    }));
    expect((await patch).patch).toMatchObject({
      boardId: board!.id,
      operation: "item.create",
      final: true
    });
    await app.close();
  });

  it("오래된 항목 버전에는 최신 스냅숏으로 응답합니다", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const owner = await repo.upsertUser({ handle: "owner", displayName: "보드 소유자" });
    const [board] = await repo.listBoards(owner.id);
    const initial = await repo.getBoardSnapshot(board!.id, owner.id);
    const app = buildApp(repo);
    await app.ready();
    const socket = await loginAndConnect(app, "owner", sockets);
    const joined = next(socket, "board.snapshot");
    socket.send(JSON.stringify({ type: "board.join", boardId: board!.id }));
    await joined;

    const recovered = next(socket, "board.snapshot");
    socket.send(JSON.stringify({
      type: "item.update",
      boardId: board!.id,
      itemId: initial!.items[0]!.id,
      content: "충돌한 변경",
      baseVersion: initial!.items[0]!.version + 10
    }));
    expect((await recovered).snapshot.items[0].content).toBe(initial!.items[0]!.content);
    await app.close();
  });

  it("읽기 전용 사용자의 쓰기 요청은 연결을 종료합니다", async () => {
    const repo = createMemoryRepository();
    await repo.seed();
    const viewer = await repo.upsertUser({ handle: "viewer", displayName: "읽기 전용 사용자" });
    const [board] = await repo.listBoards(viewer.id);
    const app = buildApp(repo);
    await app.ready();
    const socket = await loginAndConnect(app, "viewer", sockets);
    const joined = next(socket, "board.snapshot");
    socket.send(JSON.stringify({ type: "board.join", boardId: board!.id }));
    await joined;

    const closeCode = closed(socket);
    socket.send(JSON.stringify({
      type: "item.create",
      boardId: board!.id,
      kind: "note",
      content: "허용되지 않은 변경",
      x: 20,
      y: 20
    }));
    expect(await closeCode).toBe(1008);
    await app.close();
  });
});
