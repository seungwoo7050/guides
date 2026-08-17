"use client";

import { useEffect, useRef, useState, type FormEvent, type PointerEvent } from "react";

import {
  BOARD_HEIGHT,
  BOARD_WIDTH,
  ServerEventSchema,
  type BoardItem,
  type BoardSnapshot,
  type ServerEvent
} from "@board/contracts";
import { reduceBoardEvent } from "../lib/boardState";
import { websocketUrl } from "../lib/api";

type DragState = {
  pointerId: number;
  itemId: string;
  baseVersion: number;
  offsetX: number;
  offsetY: number;
};

// [Implementation 9-4] Own socket reconnect, sequence recovery, role-aware commands, transient pointer previews, and final versioned persistence in one board client boundary.
export function BoardCanvas({ boardId }: { boardId: string }) {
  const [snapshot, setSnapshot] = useState<BoardSnapshot | null>(null);
  const [presence, setPresence] = useState<Array<{ userId: string; displayName: string }>>([]);
  const [status, setStatus] = useState("connecting");
  const [content, setContent] = useState("");
  const socketRef = useRef<WebSocket | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const reconnectRef = useRef<number | null>(null);

  useEffect(() => {
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      const socket = new WebSocket(websocketUrl);
      socketRef.current = socket;
      setStatus("connecting");

      socket.addEventListener("open", () => {
        setStatus("connected");
        socket.send(JSON.stringify({ type: "board.join", boardId }));
      });
      socket.addEventListener("message", (message) => {
        const parsed = ServerEventSchema.safeParse(safeJson(String(message.data)));
        if (!parsed.success) return;
        const event = parsed.data;
        if (event.type === "presence.changed") {
          setPresence(event.members.map(({ userId, displayName }) => ({ userId, displayName })));
          return;
        }
        setSnapshot((current) => {
          const reduced = reduceBoardEvent(current, event);
          if (reduced.needsSnapshot && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "snapshot.request", boardId }));
          }
          if (reduced.closedReason) setStatus(`closed: ${reduced.closedReason}`);
          return reduced.snapshot;
        });
      });
      socket.addEventListener("close", () => {
        socketRef.current = null;
        if (disposed) return;
        setStatus("reconnecting");
        reconnectRef.current = window.setTimeout(connect, 1_000);
      });
      socket.addEventListener("error", () => socket.close());
    };

    connect();
    return () => {
      disposed = true;
      if (reconnectRef.current !== null) window.clearTimeout(reconnectRef.current);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [boardId]);

  const canWrite = snapshot?.role === "owner" || snapshot?.role === "editor";

  function send(event: unknown): void {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(event));
    }
  }

  function createItem(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const normalized = content.trim();
    if (!normalized || !canWrite || snapshot?.closed) return;
    send({ type: "item.create", boardId, kind: "note", content: normalized, x: 80, y: 80 });
    setContent("");
  }

  function updateItem(item: BoardItem): void {
    if (!canWrite || snapshot?.closed) return;
    const next = window.prompt("Updated content", item.content)?.trim();
    if (!next || next === item.content) return;
    send({ type: "item.update", boardId, itemId: item.id, content: next, baseVersion: item.version });
  }

  function beginDrag(event: PointerEvent<HTMLButtonElement>, item: BoardItem): void {
    if (!canWrite || snapshot?.closed) return;
    const canvas = event.currentTarget.closest(".board-canvas")?.getBoundingClientRect();
    if (!canvas) return;
    const point = toBoardPoint(event.clientX, event.clientY, canvas);
    event.currentTarget.setPointerCapture(event.pointerId);
    dragRef.current = {
      pointerId: event.pointerId,
      itemId: item.id,
      baseVersion: item.version,
      offsetX: point.x - item.x,
      offsetY: point.y - item.y
    };
  }

  function moveDrag(event: PointerEvent<HTMLButtonElement>): void {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId || !snapshot) return;
    const canvas = event.currentTarget.closest(".board-canvas")?.getBoundingClientRect();
    const item = snapshot.items.find((candidate) => candidate.id === drag.itemId);
    if (!canvas || !item) return;
    const point = toBoardPoint(event.clientX, event.clientY, canvas);
    const x = clamp(point.x - drag.offsetX, 0, BOARD_WIDTH - item.width);
    const y = clamp(point.y - drag.offsetY, 0, BOARD_HEIGHT - item.height);
    setSnapshot((current) => current ? {
      ...current,
      items: current.items.map((candidate) => candidate.id === item.id ? { ...candidate, x, y } : candidate)
    } : current);
    send({ type: "item.move", boardId, itemId: item.id, x, y, baseVersion: drag.baseVersion, final: false });
  }

  function endDrag(event: PointerEvent<HTMLButtonElement>): void {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId || !snapshot) return;
    const item = snapshot.items.find((candidate) => candidate.id === drag.itemId);
    dragRef.current = null;
    if (!item) return;
    send({
      type: "item.move",
      boardId,
      itemId: item.id,
      x: item.x,
      y: item.y,
      baseVersion: drag.baseVersion,
      final: true
    });
  }

  if (!snapshot) return <main><h1>Board</h1><p role="status">{status}</p></main>;

  return <main className="wide-main">
    <div className="board-toolbar">
      <div>
        <h1>{snapshot.title}</h1>
        <p role="status">{status} · {snapshot.role} · sequence {snapshot.sequence}</p>
      </div>
      <form className="inline-form" onSubmit={createItem}>
        <label htmlFor="new-note">New note</label>
        <input id="new-note" value={content} onChange={(event) => setContent(event.target.value)} disabled={!canWrite || snapshot.closed} />
        <button disabled={!canWrite || snapshot.closed}>Add</button>
      </form>
    </div>
    <p>Present: {presence.map((member) => member.displayName).join(", ") || "only you"}</p>
    <div
      className="board-canvas"
      style={{ aspectRatio: `${BOARD_WIDTH} / ${BOARD_HEIGHT}` }}
      onPointerMove={(event) => {
        const point = toBoardPoint(event.clientX, event.clientY, event.currentTarget.getBoundingClientRect());
        send({ type: "cursor.move", boardId, x: point.x, y: point.y });
      }}
    >
      {snapshot.items.map((item) => <article
        className={`board-item ${item.kind}`}
        key={item.id}
        style={{
          left: `${item.x / BOARD_WIDTH * 100}%`,
          top: `${item.y / BOARD_HEIGHT * 100}%`,
          width: `${item.width / BOARD_WIDTH * 100}%`,
          minHeight: `${item.height / BOARD_HEIGHT * 100}%`
        }}
      >
        <button
          className="drag-handle"
          type="button"
          aria-label={`Move ${item.content}`}
          onPointerDown={(event) => beginDrag(event, item)}
          onPointerMove={moveDrag}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          disabled={!canWrite || snapshot.closed}
        >Move</button>
        <p>{item.content}</p>
        <button type="button" onClick={() => updateItem(item)} disabled={!canWrite || snapshot.closed}>Edit</button>
        <small>v{item.version}</small>
      </article>)}
    </div>
  </main>;
}

function safeJson(value: string): unknown {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function toBoardPoint(clientX: number, clientY: number, bounds: DOMRect): { x: number; y: number } {
  return {
    x: clamp((clientX - bounds.left) / bounds.width * BOARD_WIDTH, 0, BOARD_WIDTH),
    y: clamp((clientY - bounds.top) / bounds.height * BOARD_HEIGHT, 0, BOARD_HEIGHT)
  };
}
