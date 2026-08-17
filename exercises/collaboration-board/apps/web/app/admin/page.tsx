"use client";

import { useCallback, useEffect, useState } from "react";

import {
  listAdminActions,
  listAdminUsers,
  setUserStatus,
  type AdminAction,
  type AdminUser
} from "../../lib/api";

export default function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [actions, setActions] = useState<AdminAction[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [nextUsers, nextActions] = await Promise.all([listAdminUsers(), listAdminActions()]);
      setUsers(nextUsers);
      setActions(nextActions);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Admin access failed.");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function toggle(user: AdminUser) {
    const status = user.status === "active" ? "suspended" : "active";
    const reason = window.prompt(`Reason to mark ${user.handle} ${status}`)?.trim();
    if (!reason) return;
    await setUserStatus(user.id, status, reason);
    await refresh();
  }

  return <main>
    <h1>Administration</h1>
    {error ? <p role="alert">{error}</p> : null}
    <div className="card-grid">
      {users.map((user) => <article className="panel" key={user.id}>
        <h2>{user.displayName}</h2>
        <p>@{user.handle} · {user.status}</p>
        <button onClick={() => void toggle(user)}>{user.status === "active" ? "Suspend" : "Restore"}</button>
      </article>)}
    </div>
    <h2>Audit actions</h2>
    <ol className="event-list">
      {actions.map((action) => <li key={action.id}>{action.action}: {action.reason}</li>)}
    </ol>
  </main>;
}
