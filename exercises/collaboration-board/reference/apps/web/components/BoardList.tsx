"use client";
import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import type { BoardSummary, SessionUser } from "@board/contracts";
import { createBoard, getMe, listBoards } from "../lib/api";
import { LoginForm } from "./LoginForm";

// [Implementation 6-5]
// session, server board 목록, 새 제목 draft와 사용자 안내 상태를 서로 다른 state로 둡니다.
// login 뒤에는 page reload 대신 adapter를 다시 호출해 server 정본에서 화면을 재구성합니다.
export function BoardList() {
  const [me, setMe] = useState<SessionUser | null>(null);
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [title, setTitle] = useState("");
  const [status, setStatus] = useState("보드 목록을 불러오는 중입니다.");

  async function load() {
    const user = await getMe();
    setMe(user);
    if (!user) {
      setStatus("로그인이 필요합니다.");
      return;
    }
    const result = await listBoards();
    setBoards(result);
    setStatus(result.length ? "" : "참여 중인 보드가 없습니다.");
  }
  useEffect(() => { void load(); }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const board = await createBoard(title.trim());
    setBoards((current) => [board, ...current]);
    setTitle("");
  }

  if (!me) {
    return <div className="grid gap-6 lg:grid-cols-2">
      <LoginForm onLogin={() => void load()} />
      <section className="card p-6">
        <h1 className="text-3xl font-black">실시간 협업 보드</h1>
        <p className="mt-3 text-slate-600">초대, 역할, 재연결, 충돌 복구를 한 예제에서 다룹니다.</p>
      </section>
    </div>;
  }

  return <>
    <section className="card p-6">
      <p className="text-sm font-bold text-blue-700">내 작업 공간</p>
      <h1 className="mt-2 text-3xl font-black">{me.displayName}님의 보드</h1>
      <form className="mt-5 flex gap-2" onSubmit={submit}>
        <label className="sr-only" htmlFor="board-title">새 보드 제목</label>
        <input
          className="min-w-0 flex-1 rounded border p-2"
          id="board-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="새 보드 제목"
          required
        />
        <button className="rounded bg-blue-700 px-4 py-2 font-bold text-white">만들기</button>
      </form>
    </section>
    {status ? <p role="status" className="my-4">{status}</p> : null}
    <section className="mt-5 grid gap-4 md:grid-cols-2">
      {boards.map((board) => <article className="card p-5" key={board.id}>
        <h2 className="text-xl font-black">{board.title}</h2>
        <p className="my-2 text-sm text-slate-600">역할: {roleLabel(board.role)} · 버전 {board.version}</p>
        <Link className="font-bold text-blue-700" href={`/boards/${board.id}`}>보드 열기</Link>
      </article>)}
    </section>
  </>;
}

function roleLabel(role: BoardSummary["role"]) {
  return role === "owner" ? "소유자" : role === "editor" ? "편집자" : "읽기 전용";
}
