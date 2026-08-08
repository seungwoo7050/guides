"use client";

import { useState } from "react";

export default function HomePage() {
  const [query, setQuery] = useState("");
  // TODO: 이름 변경용 제어 폼, 효과를 이용한 검색, 로딩·오류·빈 결과·성공 상태를 구현해 주세요.
  return <main>
    <h1>Frontend Exercise</h1>
    <label htmlFor="query">검색어</label>
    <input id="query" value={query} onChange={(event) => setQuery(event.target.value)} />
    <p role="status">TODO</p>
  </main>;
}
