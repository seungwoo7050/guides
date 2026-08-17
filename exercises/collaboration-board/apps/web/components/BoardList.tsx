"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import type { BoardSummary } from "@board/contracts";
import { createBoard } from "../lib/api";

export function BoardList({
  boards,
  onCreated
}: {
  boards: BoardSummary[];
  onCreated: () => void | Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = title.trim();
    if (!normalized) return;
    setPending(true);
    setError(null);
    try {
      await createBoard(normalized);
      setTitle("");
      await onCreated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The board could not be created.");
    } finally {
      setPending(false);
    }
  }

  return <>
    <form className="panel inline-form" onSubmit={submit} aria-busy={pending}>
      <label htmlFor="board-title">New board</label>
      <input
        id="board-title"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        maxLength={80}
        disabled={pending}
      />
      <button disabled={pending}>{pending ? "Creating…" : "Create"}</button>
      {error ? <p role="alert">{error}</p> : null}
    </form>
    <section aria-labelledby="boards-heading">
      <h2 id="boards-heading">Your boards</h2>
      <div className="card-grid">
        {boards.map((board) => <article className="panel" key={board.id}>
          <h3>{board.title}</h3>
          <p>{board.role} · version {board.version}{board.closed ? " · closed" : ""}</p>
          <Link href={`/boards/${board.id}`}>Open board</Link>
        </article>)}
      </div>
    </section>
  </>;
}
