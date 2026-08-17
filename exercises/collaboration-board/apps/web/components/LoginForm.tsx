"use client";

import { useState, type FormEvent } from "react";

import { login } from "../lib/api";

export function LoginForm({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [handle, setHandle] = useState("owner");
  const [displayName, setDisplayName] = useState("Board Owner");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await login({ handle, displayName });
      onAuthenticated();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Login failed.");
    } finally {
      setPending(false);
    }
  }

  return <form className="panel form-stack" onSubmit={submit}>
    <h2>Sign in</h2>
    <label htmlFor="handle">Handle</label>
    <input id="handle" value={handle} onChange={(event) => setHandle(event.target.value)} />
    <label htmlFor="display-name">Display name</label>
    <input id="display-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
    {error ? <p role="alert">{error}</p> : null}
    <button disabled={pending}>{pending ? "Signing in…" : "Sign in"}</button>
    <p className="muted">Seeded handles: owner, editor, viewer, admin.</p>
  </form>;
}
