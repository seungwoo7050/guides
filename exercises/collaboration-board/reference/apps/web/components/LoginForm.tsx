"use client";
import React, { FormEvent, useState } from "react";
import type { SessionUser } from "@board/contracts";
import { login } from "../lib/api";

// [Implementation 6-4]
// 이 form이 입력 draft와 submit failure를 소유하고, 인증된 session DTO만 상위 상태로 전달합니다.
// label, 실제 button과 alert를 유지해 pointer 없이도 같은 실패·성공 흐름을 사용할 수 있습니다.
export function LoginForm({ onLogin }: { onLogin(user: SessionUser): void }) {
  const [handle, setHandle] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      onLogin(await login({ handle: handle.trim(), displayName: displayName.trim() }));
    } catch {
      setError("로그인하지 못했습니다.");
    }
  }

  return <form className="card grid gap-3 p-5" onSubmit={submit}>
    <h2 className="text-xl font-black">로그인</h2>
    <label htmlFor="handle">핸들</label>
    <input className="rounded border p-2" id="handle" value={handle} onChange={(event) => setHandle(event.target.value)} required />
    <label htmlFor="displayName">표시 이름</label>
    <input className="rounded border p-2" id="displayName" value={displayName} onChange={(event) => setDisplayName(event.target.value)} required />
    {error ? <p role="alert">{error}</p> : null}
    <button
      className="focus-ring rounded bg-blue-700 px-4 py-2 font-bold text-white disabled:opacity-40"
      disabled={!handle.trim() || !displayName.trim()}
    >
      로그인
    </button>
  </form>;
}
