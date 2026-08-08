import { randomUUID } from "node:crypto";
import { WebSocket } from "ws";
import {
  BOARD_HEIGHT,
  BOARD_WIDTH,
  ClientEventSchema,
  type BoardPatch,
  type BoardSnapshot,
  type ServerEvent,
  type SessionUser
} from "@board/contracts";
import type { AppRepository } from "@board/db";

type Client = {
  id: string;
  socket: WebSocket;
  user: SessionUser;
  boardId: string | null;
  cursor: { x: number; y: number } | null;
  alive: boolean;
};
type Room = {
  snapshot: BoardSnapshot;
  clients: Set<Client>;
  transientSequence: number;
};

export class BoardHub {
  private readonly clients = new Map<string, Client>();
  private readonly rooms = new Map<string, Room>();
  private readonly heartbeat = setInterval(() => this.checkHeartbeat(), 15_000);

  constructor(private readonly repo: AppRepository) {}

  close() {
    clearInterval(this.heartbeat);
    for (const client of this.clients.values()) client.socket.terminate();
    this.clients.clear();
    this.rooms.clear();
  }

  connect(socket: WebSocket, user: SessionUser) {
    const client: Client = {
      id: randomUUID(),
      socket,
      user,
      boardId: null,
      cursor: null,
      alive: true
    };
    this.clients.set(client.id, client);
    socket.on("pong", () => { client.alive = true; });
    socket.on("message", (raw) => void this.receive(client, raw.toString()));
    socket.on("close", () => this.disconnect(client));
  }

  private async receive(client: Client, raw: string) {
    const parsed = ClientEventSchema.safeParse(safeJson(raw));
    if (!parsed.success) return client.socket.close(1008, "메시지 형식이 올바르지 않습니다.");
    const event = parsed.data;
    if (event.type === "board.join") return this.join(client, event.boardId);
    if (event.type === "snapshot.request") return this.sendSnapshot(client, event.boardId);
    const room = this.roomFor(client, event.boardId);
    if (!room) return client.socket.close(1008, "join board first");
    if (event.type === "cursor.move") return this.moveCursor(client, room, event.x, event.y);
    if (room.snapshot.role === "viewer") return client.socket.close(1008, "read-only member");
    if (event.type === "item.create") {
      const result = await this.repo.createItem(event.boardId, client.user.id, {
        kind: event.kind,
        content: event.content,
        x: clamp(event.x, 0, BOARD_WIDTH),
        y: clamp(event.y, 0, BOARD_HEIGHT)
      });
      room.snapshot.items.push(result.item);
      room.snapshot.version = result.boardVersion;
      room.snapshot.sequence = result.sequence;
      return this.broadcastPatch(room, {
        boardId: event.boardId,
        sequence: result.sequence,
        version: result.boardVersion,
        operation: "item.create",
        actorId: client.user.id,
        item: result.item,
        final: true
      });
    }
    if (event.type === "item.update") {
      const result = await this.repo.updateItem(
        event.boardId,
        client.user.id,
        event.itemId,
        event.content,
        event.baseVersion
      );
      if (!result) return this.sendSnapshot(client, event.boardId);
      replaceItem(room.snapshot, result.item);
      room.snapshot.version = result.boardVersion;
      room.snapshot.sequence = result.sequence;
      return this.broadcastPatch(room, {
        boardId: event.boardId,
        sequence: result.sequence,
        version: result.boardVersion,
        operation: "item.update",
        actorId: client.user.id,
        item: result.item,
        final: true
      });
    }
    if (event.type === "item.move") {
      const item = room.snapshot.items.find((candidate) => candidate.id === event.itemId);
      if (!item || item.version !== event.baseVersion) return this.sendSnapshot(client, event.boardId);
      const x = clamp(event.x, 0, BOARD_WIDTH - item.width);
      const y = clamp(event.y, 0, BOARD_HEIGHT - item.height);
      if (!event.final) {
        item.x = x;
        item.y = y;
        const sequence = ++room.transientSequence;
        return this.broadcastPatch(room, {
          boardId: event.boardId,
          sequence,
          version: room.snapshot.version,
          operation: "item.move",
          actorId: client.user.id,
          item: { ...item },
          final: false
        });
      }
      const result = await this.repo.persistItemMove(
        event.boardId,
        client.user.id,
        event.itemId,
        x,
        y,
        event.baseVersion
      );
      if (!result) return this.sendSnapshot(client, event.boardId);
      replaceItem(room.snapshot, result.item);
      room.snapshot.version = result.boardVersion;
      room.snapshot.sequence = result.sequence;
      room.transientSequence = Math.max(room.transientSequence, result.sequence);
      return this.broadcastPatch(room, {
        boardId: event.boardId,
        sequence: result.sequence,
        version: result.boardVersion,
        operation: "item.move",
        actorId: client.user.id,
        item: result.item,
        final: true
      });
    }
  }

  private async join(client: Client, boardId: string) {
    const snapshot = await this.repo.getBoardSnapshot(boardId, client.user.id);
    if (!snapshot) return client.socket.close(1008, "board membership required");
    this.leaveCurrentRoom(client);
    if (snapshot.closed) {
      this.send(client, { type: "board.closed", boardId, reason: "보드가 보관되었습니다." });
      return;
    }
    let room = this.rooms.get(boardId);
    if (!room) {
      room = { snapshot, clients: new Set(), transientSequence: snapshot.sequence };
      this.rooms.set(boardId, room);
    }
    client.boardId = boardId;
    room.clients.add(client);
    this.send(client, { type: "board.snapshot", snapshot: { ...room.snapshot, role: snapshot.role } });
    this.broadcastPresence(room);
  }

  private async sendSnapshot(client: Client, boardId: string) {
    const snapshot = await this.repo.getBoardSnapshot(boardId, client.user.id);
    if (!snapshot) return client.socket.close(1008, "board membership required");
    const room = this.rooms.get(boardId);
    if (room) room.snapshot = snapshot;
    this.send(client, { type: "board.snapshot", snapshot });
  }

  private moveCursor(client: Client, room: Room, x: number, y: number) {
    client.cursor = { x: clamp(x, 0, BOARD_WIDTH), y: clamp(y, 0, BOARD_HEIGHT) };
    const patch: BoardPatch = {
      boardId: room.snapshot.boardId,
      sequence: ++room.transientSequence,
      version: room.snapshot.version,
      operation: "cursor",
      actorId: client.user.id,
      cursor: client.cursor,
      final: false
    };
    this.broadcastPatch(room, patch);
    this.broadcastPresence(room);
  }

  private roomFor(client: Client, boardId: string) {
    return client.boardId === boardId ? this.rooms.get(boardId) ?? null : null;
  }
  private disconnect(client: Client) {
    this.leaveCurrentRoom(client);
    this.clients.delete(client.id);
  }
  private leaveCurrentRoom(client: Client) {
    if (!client.boardId) return;
    const room = this.rooms.get(client.boardId);
    room?.clients.delete(client);
    if (room) {
      this.broadcastPresence(room);
      if (room.clients.size === 0) this.rooms.delete(client.boardId);
    }
    client.boardId = null;
    client.cursor = null;
  }
  private broadcastPatch(room: Room, patch: BoardPatch) {
    for (const client of room.clients) this.send(client, { type: "board.patch", patch });
  }
  private broadcastPresence(room: Room) {
    const event: ServerEvent = {
      type: "presence.changed",
      boardId: room.snapshot.boardId,
      members: [...room.clients].map((client) => ({
        userId: client.user.id,
        displayName: client.user.displayName,
        connected: true,
        cursor: client.cursor
      }))
    };
    for (const client of room.clients) this.send(client, event);
  }
  private send(client: Client, event: ServerEvent) {
    if (client.socket.readyState === WebSocket.OPEN) client.socket.send(JSON.stringify(event));
  }
  private checkHeartbeat() {
    for (const client of this.clients.values()) {
      if (!client.alive) {
        client.socket.terminate();
        this.disconnect(client);
        continue;
      }
      client.alive = false;
      client.socket.ping();
    }
  }
}

function safeJson(raw: string) {
  try { return JSON.parse(raw); } catch { return null; }
}
function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}
function replaceItem(snapshot: BoardSnapshot, item: BoardSnapshot["items"][number]) {
  const index = snapshot.items.findIndex((candidate) => candidate.id === item.id);
  if (index >= 0) snapshot.items[index] = item;
}
