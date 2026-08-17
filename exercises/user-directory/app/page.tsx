"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { searchUsers, type User } from "../lib/fake-api";

// [Implementation 3] Represent request state as a discriminated union so loading, success, and failure cannot be true simultaneously.
type LoadState =
  | { status: "loading" }
  | { status: "success"; users: User[] }
  | { status: "error"; message: string };

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [name, setName] = useState("Visitor");
  const [draftName, setDraftName] = useState("");
  const [state, setState] = useState<LoadState>({ status: "loading" });

  // [Implementation 4] Couple every request to effect cleanup so AbortController revokes stale response ownership.
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    searchUsers(query, controller.signal)
      .then((users) => setState({ status: "success", users }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({
          status: "error",
          message: error instanceof Error ? error.message : "Search failed"
        });
      });
    return () => controller.abort();
  }, [query]);


  function commitDisplayName(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = draftName.trim();
    if (!normalized) return;
    setName(normalized);
    setDraftName("");
  }

  // [Implementation 5] Project the state union into mutually exclusive loading, error, empty, and success views, then link to the server route.
  return <main>
    <h1>Hello, {name}</h1>
    <form onSubmit={commitDisplayName}>
      <label htmlFor="name">Display name</label>
      <input
        id="name"
        value={draftName}
        onChange={(event) => setDraftName(event.target.value)}
        maxLength={40}
      />
      <button type="submit">Update</button>
    </form>

    <section aria-labelledby="search-heading">
      <h2 id="search-heading">User search</h2>
      <label htmlFor="query">Search term</label>
      <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} />
      {state.status === "loading" ? <p role="status">Loading</p> : null}
      {state.status === "error" ? <p role="alert">{state.message}</p> : null}
      {state.status === "success" && state.users.length === 0 ? <p>No results</p> : null}
      {state.status === "success" ? <div className="grid">{state.users.map((user) =>
        <article className="card" key={user.id}>
          <h3>{user.displayName}</h3>
          <p>@{user.handle}</p>
          <Link href={`/profile/${user.handle}`}>Profile</Link>
        </article>
      )}</div> : null}
    </section>
  </main>;
}
