import { randomUUID } from "node:crypto";
import websocket from "@fastify/websocket";
import Fastify, { type FastifyRequest } from "fastify";
import { WebSocket } from "ws";
import { ClientEventSchema, type BoardSnapshot, type ServerEvent } from "./protocol";

// [Implementation 2] app instance가 client connection과 board snapshot의 수명을 소유하도록 state model을 먼저 정의합니다.
type Role = "editor" | "viewer";
type Client = {
  id: string;
  socket: WebSocket;
  boardId: string | null;
  alive: boolean;
  role: Role;
};
type ResolveRole = (request: FastifyRequest) => Role;

export async function buildApp(resolveRole: ResolveRole = () => "editor") {
  const app = Fastify({ logger: false });
  const clients = new Set<Client>();
  const boards = new Map<string, BoardSnapshot>();
  await app.register(websocket);

  // [Implementation 3] connection handler는 listener를 등록하고 모든 message를 parse한 뒤 join-before-write를 강제합니다.
  app.get("/ws", { websocket: true }, (socket, request) => {
    const client: Client = {
      id: randomUUID(),
      socket: socket as WebSocket,
      boardId: null,
      alive: true,
      role: resolveRole(request)
    };
    clients.add(client);
    socket.on("pong", () => { client.alive = true; });
    socket.on("close", () => clients.delete(client));
    socket.on("message", (raw) => {
      const parsed = ClientEventSchema.safeParse(safeJson(raw.toString()));
      if (!parsed.success) return socket.close(1008, "메시지 형식이 올바르지 않습니다.");
      const event = parsed.data;
      if (event.type === "board.join") {
        client.boardId = event.boardId;
        send(client, { type: "board.snapshot", snapshot: board(event.boardId) });
        return presence(event.boardId);
      }
      if (client.boardId !== event.boardId) return socket.close(1008, "join board first");
      if (event.type === "snapshot.request") {
        return send(client, { type: "board.snapshot", snapshot: board(event.boardId) });
      }
      // [Implementation 5] 읽기 전용 role의 영속 write는 client UI가 아니라 server connection boundary에서 거부합니다.
      if (client.role === "viewer" && event.type !== "cursor.move") {
        return client.socket.close(1008, "write permission required");
      }
      const current = board(event.boardId);
      // [Implementation 6] 새 항목은 item, board version과 sequence를 한 server-owned state transition으로 전진시킵니다.
      if (event.type === "item.create") {
        current.version += 1;
        current.sequence += 1;
        current.items.push({
          id: randomUUID(),
          content: event.content,
          x: event.x,
          y: event.y,
          version: 1
        });
      }
      // [Implementation 7] update와 move는 baseVersion을 검사하고 transient preview와 final persistence를 구분합니다.
      if (event.type === "item.update" || event.type === "item.move") {
        const item = current.items.find((candidate) => candidate.id === event.itemId);
        if (!item || item.version !== event.baseVersion) {
          return send(client, { type: "board.snapshot", snapshot: current });
        }
        if (event.type === "item.update") item.content = event.content;
        if (event.type === "item.move") {
          if (!event.final) {
            const preview = {
              type: "item.preview" as const,
              preview: {
                boardId: event.boardId,
                itemId: event.itemId,
                x: event.x,
                y: event.y,
                baseVersion: event.baseVersion
              }
            };
            for (const target of clients) if (target.boardId === event.boardId) send(target, preview);
            return;
          }
          item.x = event.x;
          item.y = event.y;
        }
        item.version += 1;
        current.version += 1;
        current.sequence += 1;
      }
      const patch = {
        type: "board.patch" as const,
        patch: { boardId: event.boardId, sequence: current.sequence, operation: event.type }
      };
      for (const target of clients) if (target.boardId === event.boardId) send(target, patch);
    });
  });

  // [Implementation 8] heartbeat timer와 socket collection을 app onClose에 묶어 성공·실패 뒤 열린 handle을 남기지 않습니다.
  const heartbeat = setInterval(() => {
    for (const client of clients) {
      if (!client.alive) {
        client.socket.terminate();
        clients.delete(client);
        continue;
      }
      client.alive = false;
      client.socket.ping();
    }
  }, 10_000);

  app.addHook("onClose", async () => {
    clearInterval(heartbeat);
    for (const client of clients) client.socket.terminate();
    clients.clear();
  });

  // [Implementation 4] board와 presence helper가 room별 snapshot 및 참가자 projection의 단일 owner가 됩니다.
  function board(boardId: string) {
    const current = boards.get(boardId) ?? { boardId, version: 0, sequence: 0, items: [] };
    boards.set(boardId, current);
    return current;
  }
  function presence(boardId: string) {
    const members = [...clients].filter((client) => client.boardId === boardId).map((client) => client.id);
    for (const target of clients) {
      if (target.boardId === boardId) send(target, { type: "presence.changed", boardId, members });
    }
  }
  return app;
}

function send(client: Client, event: ServerEvent) {
  if (client.socket.readyState === WebSocket.OPEN) client.socket.send(JSON.stringify(event));
}
function safeJson(raw: string) {
  try { return JSON.parse(raw); } catch { return null; }
}
