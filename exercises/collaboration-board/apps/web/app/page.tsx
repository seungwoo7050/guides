"use client";

import { useCallback, useEffect, useState } from "react";

import type { BoardSummary, SessionUser } from "@board/contracts";
import { BoardList } from "../components/BoardList";
import { LoginForm } from "../components/LoginForm";
import { ApiError, getMe, listBoards, logout } from "../lib/api";

// [Implementation 9-2] Coordinate session discovery, login recovery, board loading, creation refresh, and logout as one mutually exclusive application state.
export default function HomePage() {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const current = await getMe();
      setUser(current);
      setBoards(await listBoards());
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setUser(null);
        setBoards([]);
      } else {
        setError(caught instanceof Error ? caught.message : "Failed to load the application.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (loading) return <main><h1>Boards</h1><p role="status">Loading…</p></main>;
  if (!user) return <main>
    <h1>Collaboration Board</h1>
    {error ? <p role="alert">{error}</p> : null}
    <LoginForm onAuthenticated={refresh} />
  </main>;

  return <main>
    <div className="page-heading">
      <div><h1>Boards</h1><p>Signed in as {user.displayName} (@{user.handle})</p></div>
      <button onClick={() => void logout().then(refresh)}>Sign out</button>
    </div>
    {error ? <p role="alert">{error}</p> : null}
    <BoardList boards={boards} onCreated={refresh} />
  </main>;
}
