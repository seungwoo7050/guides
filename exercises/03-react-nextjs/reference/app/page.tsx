"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { searchUsers, type User } from "../lib/fake-api";

// [Implementation 3] 요청 상태를 판별 가능한 union으로 두어 loading, success와 failure가 동시에 참이 되지 않게 합니다.
type LoadState =
  | { status: "loading" }
  | { status: "success"; users: User[] }
  | { status: "error"; message: string };

export default function HomePage() {
  const [query, setQuery] = useState("");
  const [name, setName] = useState("방문자");
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const nameInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // [Implementation 4] effect가 시작한 요청을 cleanup의 AbortController가 끝내 오래된 응답의 state 소유권을 회수합니다.
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    searchUsers(query, controller.signal)
      .then((users) => setState({ status: "success", users }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setState({ status: "error", message: error instanceof Error ? error.message : "검색 실패" });
      });
    return () => controller.abort();
  }, [query]);

  useEffect(() => {
    const nameInput = nameInputRef.current;
    if (!nameInput) return;

    const onInput = (event: Event) => {
      const next = ((event.target as HTMLInputElement | null)?.value ?? "").trim();
      if (next) setName(next);
    };
    nameInput.addEventListener("input", onInput);
    return () => nameInput.removeEventListener("input", onInput);
  }, []);

  useEffect(() => {
    const form = formRef.current;
    if (!form) return;
    const onSubmit = (event: Event) => {
      event.preventDefault();
      form.reset();
    };
    form.addEventListener("submit", onSubmit);
    return () => form.removeEventListener("submit", onSubmit);
  }, []);

  // [Implementation 5] 상태 union을 loading·error·empty·success의 배타적인 화면으로 투영하고 server route로 연결합니다.
  return <main>
    <h1>안녕하세요, {name}</h1>
    <form ref={formRef}>
      <label htmlFor="name">표시 이름</label>
      <input id="name" ref={nameInputRef} />
      <button type="submit">변경</button>
    </form>

    <section aria-labelledby="search-heading">
      <h2 id="search-heading">사용자 검색</h2>
      <label htmlFor="query">검색어</label>
      <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} />
      {state.status === "loading" ? <p role="status">불러오는 중</p> : null}
      {state.status === "error" ? <p role="alert">{state.message}</p> : null}
      {state.status === "success" && state.users.length === 0 ? <p>결과 없음</p> : null}
      {state.status === "success" ? <div className="grid">{state.users.map((user) =>
        <article className="card" key={user.id}>
          <h3>{user.displayName}</h3>
          <p>@{user.handle}</p>
          <Link href={`/profile/${user.handle}`}>프로필</Link>
        </article>
      )}</div> : null}
    </section>
  </main>;
}
