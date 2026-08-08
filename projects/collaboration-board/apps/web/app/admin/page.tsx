"use client";
import { useEffect, useState } from "react";
import { AppShell } from "../../components/AppShell";
import { getAdminUsers, setUserStatus } from "../../lib/api";

export default function AdminPage() {
  const [users, setUsers] = useState<Awaited<ReturnType<typeof getAdminUsers>>>([]);
  const [reason, setReason] = useState("운영 정책 검토");
  const [message, setMessage] = useState("");
  const load = () => getAdminUsers().then(setUsers).catch(() => setMessage("운영자 권한이 필요합니다."));
  useEffect(() => { void load(); }, []);

  async function toggle(user: Awaited<ReturnType<typeof getAdminUsers>>[number]) {
    const status = user.status === "active" ? "suspended" : "active";
    await setUserStatus(user.id, status, reason);
    setMessage("계정 상태와 감사 기록을 함께 변경했습니다.");
    await load();
  }

  return <AppShell>
    <h1 className="text-3xl font-black">관리 작업</h1>
    <label htmlFor="reason">조치 사유</label>
    <input
      id="reason"
      className="m-3 rounded border p-2"
      value={reason}
      onChange={(event) => setReason(event.target.value)}
    />
    {message ? <p role="status">{message}</p> : null}
    <div className="mt-4 grid gap-3">
      {users.map((user) => <article className="card flex items-center justify-between p-4" key={user.id}>
        <span>{user.displayName} · {user.status === "active" ? "활성" : "정지"}</span>
        <button className="rounded bg-slate-800 px-3 py-2 text-white" onClick={() => toggle(user)}>
          {user.status === "active" ? "정지" : "복구"}
        </button>
      </article>)}
    </div>
  </AppShell>;
}
