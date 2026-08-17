import { randomUUID } from "node:crypto";

import websocket from "@fastify/websocket";
import Fastify, { type FastifyRequest } from "fastify";
import type { RawData, WebSocket } from "ws";

import { ConnectionHub, type ClientConnection, type Role } from "./hub";
import { ClientEventSchema, type ClientEvent } from "./protocol";
import { BoardStore, type MutationResult } from "./state";

export interface RealtimeAppOptions {
  resolveRole?: (request: FastifyRequest) => Role;
  heartbeatIntervalMs?: number;
}

// [Implementation 5] Compose the WebSocket transport with app-owned board and connection state so each server instance has an independent lifecycle.
export async function buildApp({
  resolveRole = () => "editor",
  heartbeatIntervalMs = 10_000
}: RealtimeAppOptions = {}) {
  if (!Number.isFinite(heartbeatIntervalMs) || heartbeatIntervalMs <= 0) {
    throw new RangeError("heartbeatIntervalMs must be positive");
  }

  const app = Fastify({ logger: false });
  const boards = new BoardStore();
  const hub = new ConnectionHub();
  await app.register(websocket);

  // [Implementation 6] Establish connection ownership, validate every message, and enforce join-before-use before dispatching protocol behavior.
  app.get("/ws", { websocket: true }, (socket, request) => {
    const client: ClientConnection = {
      id: randomUUID(),
      socket: socket as WebSocket,
      boardId: null,
      alive: true,
      role: resolveRole(request)
    };
    hub.add(client);

    socket.on("pong", () => {
      client.alive = true;
    });
    socket.on("close", () => {
      hub.remove(client);
    });
    socket.on("message", (raw: RawData) => {
      const parsed = ClientEventSchema.safeParse(safeJson(String(raw)));
      if (!parsed.success) {
        client.socket.close(1008, "invalid message");
        return;
      }
      dispatch(client, parsed.data);
    });
  });

  function dispatch(client: ClientConnection, event: ClientEvent): void {
    if (event.type === "board.join") {
      hub.join(client, event.boardId);
      hub.send(client, { type: "board.snapshot", snapshot: boards.snapshot(event.boardId) });
      return;
    }

    if (client.boardId !== event.boardId) {
      client.socket.close(1008, "join board first");
      return;
    }

    if (event.type === "snapshot.request") {
      hub.send(client, { type: "board.snapshot", snapshot: boards.snapshot(event.boardId) });
      return;
    }

    if (event.type === "cursor.move") {
      hub.broadcast(event.boardId, {
        type: "cursor.moved",
        cursor: { boardId: event.boardId, clientId: client.id, x: event.x, y: event.y }
      });
      return;
    }

    // [Implementation 7] Enforce persistent-write authorization at the server connection boundary rather than relying on client controls.
    if (client.role === "viewer") {
      client.socket.close(1008, "write permission required");
      return;
    }

    const result = mutate(event);

    // [Implementation 8] Recover stale writes with a current snapshot, broadcast previews without sequence changes, and publish committed patches room-wide.
    if (result.kind === "stale") {
      hub.send(client, { type: "board.snapshot", snapshot: result.snapshot });
      return;
    }
    hub.broadcast(event.boardId, result.event);
  }

  function mutate(event: Exclude<ClientEvent, { type: "board.join" | "snapshot.request" | "cursor.move" }>): MutationResult {
    if (event.type === "item.create") {
      return boards.createItem(event.boardId, event);
    }
    if (event.type === "item.update") {
      return boards.updateItem(event.boardId, event);
    }
    return boards.moveItem(event.boardId, event);
  }

  // [Implementation 9] Bind heartbeat ownership and socket teardown to the Fastify lifecycle so no timer or connection survives application close.
  const heartbeat = setInterval(() => {
    for (const client of hub.all()) {
      if (!client.alive) {
        client.socket.terminate();
        hub.remove(client);
        continue;
      }
      client.alive = false;
      client.socket.ping();
    }
  }, heartbeatIntervalMs);
  heartbeat.unref();

  app.addHook("onClose", async () => {
    clearInterval(heartbeat);
    hub.closeAll();
  });

  return app;
}

function safeJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
