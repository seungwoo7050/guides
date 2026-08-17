import { randomUUID } from "node:crypto";

import { WebSocket } from "ws";

import {
  BOARD_HEIGHT,
  BOARD_WIDTH,
  ClientEventSchema,
  DEFAULT_ITEM_HEIGHT,
  DEFAULT_ITEM_WIDTH,
  type BoardPatch,
  type BoardRole,
  type BoardSnapshot,
  type ServerEvent,
  type SessionUser
} from "@board/contracts";
import { RepositoryError, type AppRepository } from "@board/db";

type Client = {
  id: string;
  socket: WebSocket;
  user: SessionUser;
  boardId: string | null;
  boardRole: BoardRole | null;
  cursor: { x: number; y: number } | null;
  alive: boolean;
};

type Room = {
  snapshot: BoardSnapshot;
  clients: Set<Client>;
  transientSequence: number;
};

// [Implementation 7] Own connection, room, presence, cached snapshot, transient delivery, and heartbeat state in one server-side realtime hub.
export class BoardHub {
  private readonly clients = new Map<string, Client>();
  private readonly rooms = new Map<string, Room>();
  private readonly heartbeat: NodeJS.Timeout;

  constructor(
    private readonly repo: AppRepository,
    heartbeatIntervalMs = 15_000
  ) {
    this.heartbeat = setInterval(() => this.checkHeartbeat(), heartbeatIntervalMs);
    this.heartbeat.unref();
  }

  close(): void {
    clearInterval(this.heartbeat);
    for (const client of this.clients.values()) client.socket.terminate();
    this.clients.clear();
    this.rooms.clear();
  }

  connect(socket: WebSocket, user: SessionUser): void {
    const client: Client = {
      id: randomUUID(),
      socket,
      user,
      boardId: null,
      boardRole: null,
      cursor: null,
      alive: true
    };
    this.clients.set(client.id, client);
    socket.on("pong", () => {
      client.alive = true;
    });
    socket.on("message", (raw) => {
      void this.receive(client, String(raw)).catch((error: unknown) => {
        if (error instanceof RepositoryError && ["read_only", "board_closed", "forbidden"].includes(error.code)) {
          client.socket.close(1008, error.code);
          return;
        }
        client.socket.close(1011, "message processing failed");
      });
    });
    socket.on("close", () => this.disconnect(client));
  }

  broadcastBoardClosed(boardId: string, reason: string): void {
    const room = this.rooms.get(boardId);
    if (!room) return;
    for (const client of room.clients) {
      this.send(client, { type: "board.closed", boardId, reason });
      client.socket.close(1000, "board closed");
    }
    this.rooms.delete(boardId);
  }

  disconnectUser(userId: string, reason: string): void {
    for (const client of [...this.clients.values()]) {
      if (client.user.id !== userId) continue;
      client.socket.close(1008, reason);
      this.disconnect(client);
    }
  }

  disconnectBoardMember(boardId: string, userId: string, reason: string): void {
    for (const client of [...this.clients.values()]) {
      if (client.boardId !== boardId || client.user.id !== userId) continue;
      client.socket.close(1008, reason);
      this.disconnect(client);
    }
  }

  private async receive(client: Client, raw: string): Promise<void> {
    const parsed = ClientEventSchema.safeParse(safeJson(raw));
    if (!parsed.success) {
      client.socket.close(1008, "invalid message");
      return;
    }
    const event = parsed.data;

    // [Implementation 7-1] Resolve membership on join, bind the role to the individual connection, and require that room identity before every later event.
    if (event.type === "board.join") {
      await this.join(client, event.boardId);
      return;
    }
    if (client.boardId !== event.boardId || !client.boardRole) {
      client.socket.close(1008, "join board first");
      return;
    }
    if (event.type === "snapshot.request") {
      await this.sendSnapshot(client, event.boardId);
      return;
    }

    const room = this.rooms.get(event.boardId);
    if (!room) {
      await this.sendSnapshot(client, event.boardId);
      return;
    }

    if (event.type === "cursor.move") {
      this.moveCursor(client, room, event.x, event.y);
      return;
    }
    if (client.boardRole === "viewer") {
      client.socket.close(1008, "read-only member");
      return;
    }

    // [Implementation 7-2] Broadcast only repository-confirmed persistent transitions and recover stale item versions with a fresh member-specific snapshot.
    if (event.type === "item.create") {
      const result = await this.repo.createItem(event.boardId, client.user.id, {
        kind: event.kind,
        content: event.content,
        x: clamp(event.x, 0, BOARD_WIDTH - DEFAULT_ITEM_WIDTH),
        y: clamp(event.y, 0, BOARD_HEIGHT - DEFAULT_ITEM_HEIGHT)
      });
      room.snapshot.items.push(result.item);
      room.snapshot.version = result.boardVersion;
      room.snapshot.sequence = result.sequence;
      this.broadcastPatch(room, {
        boardId: event.boardId,
        sequence: result.sequence,
        version: result.boardVersion,
        operation: "item.create",
        actorId: client.user.id,
        item: result.item,
        final: true
      });
      return;
    }

    if (event.type === "item.update") {
      const result = await this.repo.updateItem(
        event.boardId,
        client.user.id,
        event.itemId,
        event.content,
        event.baseVersion
      );
      if (!result) {
        await this.sendSnapshot(client, event.boardId);
        return;
      }
      replaceItem(room.snapshot, result.item);
      room.snapshot.version = result.boardVersion;
      room.snapshot.sequence = result.sequence;
      this.broadcastPatch(room, {
        boardId: event.boardId,
        sequence: result.sequence,
        version: result.boardVersion,
        operation: "item.update",
        actorId: client.user.id,
        item: result.item,
        final: true
      });
      return;
    }

    const item = room.snapshot.items.find((candidate) => candidate.id === event.itemId);
    if (!item || item.version !== event.baseVersion) {
      await this.sendSnapshot(client, event.boardId);
      return;
    }
    const x = clamp(event.x, 0, BOARD_WIDTH - item.width);
    const y = clamp(event.y, 0, BOARD_HEIGHT - item.height);

    // [Implementation 7-3] Keep cursor and drag previews outside durable board state, then bind final motion, heartbeat, disconnect, and room cleanup to explicit lifecycles.
    if (!event.final) {
      this.broadcastPatch(room, {
        boardId: event.boardId,
        sequence: ++room.transientSequence,
        version: room.snapshot.version,
        operation: "item.move",
        actorId: client.user.id,
        item: { ...item, x, y },
        final: false
      });
      return;
    }

    const result = await this.repo.persistItemMove(
      event.boardId,
      client.user.id,
      event.itemId,
      x,
      y,
      event.baseVersion
    );
    if (!result) {
      await this.sendSnapshot(client, event.boardId);
      return;
    }
    replaceItem(room.snapshot, result.item);
    room.snapshot.version = result.boardVersion;
    room.snapshot.sequence = result.sequence;
    room.transientSequence = Math.max(room.transientSequence, result.sequence);
    this.broadcastPatch(room, {
      boardId: event.boardId,
      sequence: result.sequence,
      version: result.boardVersion,
      operation: "item.move",
      actorId: client.user.id,
      item: result.item,
      final: true
    });
  }

  private async join(client: Client, boardId: string): Promise<void> {
    const snapshot = await this.repo.getBoardSnapshot(boardId, client.user.id);
    if (!snapshot) {
      client.socket.close(1008, "board membership required");
      return;
    }
    this.leaveCurrentRoom(client);
    if (snapshot.closed) {
      this.send(client, { type: "board.closed", boardId, reason: "board is closed" });
      return;
    }

    let room = this.rooms.get(boardId);
    if (!room) {
      room = { snapshot: { ...snapshot, items: snapshot.items.map((item) => ({ ...item })) }, clients: new Set(), transientSequence: snapshot.sequence };
      this.rooms.set(boardId, room);
    }
    client.boardId = boardId;
    client.boardRole = snapshot.role;
    room.clients.add(client);
    this.send(client, {
      type: "board.snapshot",
      snapshot: { ...room.snapshot, role: snapshot.role, items: room.snapshot.items.map((item) => ({ ...item })) }
    });
    this.broadcastPresence(room);
  }

  private async sendSnapshot(client: Client, boardId: string): Promise<void> {
    const snapshot = await this.repo.getBoardSnapshot(boardId, client.user.id);
    if (!snapshot) {
      client.socket.close(1008, "board membership required");
      return;
    }
    const room = this.rooms.get(boardId);
    if (room) {
      room.snapshot = { ...snapshot, items: snapshot.items.map((item) => ({ ...item })) };
      room.transientSequence = Math.max(room.transientSequence, snapshot.sequence);
    }
    this.send(client, { type: "board.snapshot", snapshot });
  }

  private moveCursor(client: Client, room: Room, x: number, y: number): void {
    client.cursor = { x: clamp(x, 0, BOARD_WIDTH), y: clamp(y, 0, BOARD_HEIGHT) };
    this.broadcastPatch(room, {
      boardId: room.snapshot.boardId,
      sequence: ++room.transientSequence,
      version: room.snapshot.version,
      operation: "cursor",
      actorId: client.user.id,
      cursor: client.cursor,
      final: false
    });
    this.broadcastPresence(room);
  }

  private disconnect(client: Client): void {
    this.leaveCurrentRoom(client);
    this.clients.delete(client.id);
  }

  private leaveCurrentRoom(client: Client): void {
    if (!client.boardId) return;
    const boardId = client.boardId;
    const room = this.rooms.get(boardId);
    room?.clients.delete(client);
    client.boardId = null;
    client.boardRole = null;
    client.cursor = null;
    if (!room) return;
    if (room.clients.size === 0) this.rooms.delete(boardId);
    else this.broadcastPresence(room);
  }

  private broadcastPatch(room: Room, patch: BoardPatch): void {
    for (const client of room.clients) this.send(client, { type: "board.patch", patch });
  }

  private broadcastPresence(room: Room): void {
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

  private send(client: Client, event: ServerEvent): void {
    if (client.socket.readyState === WebSocket.OPEN) client.socket.send(JSON.stringify(event));
  }

  private checkHeartbeat(): void {
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

function safeJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function replaceItem(snapshot: BoardSnapshot, item: BoardSnapshot["items"][number]): void {
  const index = snapshot.items.findIndex((candidate) => candidate.id === item.id);
  if (index >= 0) snapshot.items[index] = { ...item };
}
