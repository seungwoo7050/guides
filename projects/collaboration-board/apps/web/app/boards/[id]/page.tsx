"use client";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ServerEventSchema, type BoardSnapshot } from "@board/contracts";
import { AppShell } from "../../../components/AppShell";
import { BoardCanvas } from "../../../components/BoardCanvas";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:4000/ws";

export default function BoardPage() {
  const { id: boardId } = useParams<{ id: string }>();
  const [snapshot, setSnapshot] = useState<BoardSnapshot | null>(null);
  const [status, setStatus] = useState("연결 전");
  const [presence, setPresence] = useState<string[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (!boardId) return;
    stoppedRef.current = false;
    connect();
    return () => {
      stoppedRef.current = true;
      socketRef.current?.close();
    };
  }, [boardId]);

  function connect() {
    const socket = new WebSocket(WS_URL);
    socketRef.current = socket;
    socket.onopen = () => {
      retryRef.current = 0;
      setStatus("연결되었습니다.");
      socket.send(JSON.stringify({ type: "board.join", boardId }));
    };
    socket.onmessage = (event) => {
      const parsed = ServerEventSchema.safeParse(JSON.parse(event.data));
      if (!parsed.success) return;
      const message = parsed.data;
      if (message.type === "board.snapshot") setSnapshot(message.snapshot);
      if (message.type === "board.patch") {
        setSnapshot((current) => {
          if (!current || message.patch.boardId !== current.boardId) return current;
          const next = structuredClone(current);
          next.sequence = Math.max(next.sequence, message.patch.sequence);
          next.version = Math.max(next.version, message.patch.version);
          if (message.patch.item) {
            const index = next.items.findIndex((item) => item.id === message.patch.item!.id);
            if (index >= 0) next.items[index] = message.patch.item;
            else next.items.push(message.patch.item);
          }
          return next;
        });
      }
      if (message.type === "presence.changed") {
        setPresence(message.members.map((member) => member.displayName));
      }
      if (message.type === "board.closed") setStatus(message.reason);
    };
    socket.onclose = (event) => {
      socketRef.current = null;
      if (stoppedRef.current || event.code === 1008) {
        if (event.code === 1008) setStatus(event.reason || "접근이 거부되었습니다.");
        return;
      }
      setStatus("연결을 복구하는 중입니다.");
      const delay = Math.min(5_000, 500 * 2 ** retryRef.current++);
      setTimeout(connect, delay + Math.random() * 200);
    };
  }
  function send(message: unknown) {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  }

  return <AppShell>
    <div className="grid gap-5 xl:grid-cols-[1fr_18rem]">
      <section>
        <h1 className="text-3xl font-black">{snapshot?.title ?? "협업 보드"}</h1>
        <p role="status" className="my-3">{status}</p>
        <BoardCanvas
          snapshot={snapshot}
          onPointer={(x, y, create) => {
            if (create && snapshot?.role !== "viewer") {
              send({ type: "item.create", boardId, kind: "note", content: "새 메모", x, y });
            } else {
              send({ type: "cursor.move", boardId, x, y });
            }
          }}
        />
      </section>
      <aside className="card p-5">
        <h2 className="text-xl font-black">현재 참여자</h2>
        <ul className="my-3">{presence.map((name) => <li key={name}>{name}</li>)}</ul>
        <p className="text-sm text-slate-600">
          {snapshot?.role === "viewer"
            ? "읽기 전용으로 참여 중입니다."
            : "빈 곳을 두 번 누르면 메모를 추가합니다."}
        </p>
        <button
          className="mt-4 rounded border px-3 py-2"
          onClick={() => send({ type: "snapshot.request", boardId })}
        >
          최신 상태 다시 받기
        </button>
      </aside>
    </div>
  </AppShell>;
}
