"use client";

import { useEffect, useState } from "react";

import type { BoardSummary } from "@board/contracts";
import { listActivity, listBoards, type BoardEvent } from "../../lib/api";

// [Implementation 9-5] Project durable board events and administrator actions through operational pages without bypassing the same credentialed API boundary.
export default function ActivityPage() {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [boardId, setBoardId] = useState("");
  const [events, setEvents] = useState<BoardEvent[]>([]);

  useEffect(() => {
    void listBoards().then((result) => {
      setBoards(result);
      setBoardId(result[0]?.id ?? "");
    });
  }, []);

  useEffect(() => {
    if (!boardId) return;
    void listActivity(boardId).then(setEvents);
  }, [boardId]);

  return <main>
    <h1>Activity</h1>
    <label htmlFor="activity-board">Board</label>
    <select id="activity-board" value={boardId} onChange={(event) => setBoardId(event.target.value)}>
      {boards.map((board) => <option value={board.id} key={board.id}>{board.title}</option>)}
    </select>
    <ol className="event-list">
      {events.map((event) => <li key={event.id}>
        <strong>{event.eventType}</strong> · sequence {event.sequence} · {new Date(event.createdAt).toLocaleString()}
      </li>)}
    </ol>
  </main>;
}
