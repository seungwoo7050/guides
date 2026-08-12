// [Implementation 3] 정적 검색 자료와 DOM handle을 한 module이 소유해 UI projection의 입력 경계를 정합니다.
const documents = [
  { id: "runtime", title: "JavaScript runtime", body: "call stack, task, microtask와 취소" },
  { id: "browser", title: "Browser platform", body: "DOM, CSS, accessibility와 history" },
  { id: "api", title: "HTTP API", body: "runtime validation과 오류 계약" },
  { id: "realtime", title: "Realtime state", body: "WebSocket room, snapshot, reconnect" }
];

const form = document.querySelector("#search-form");
const input = document.querySelector("#query");
const results = document.querySelector("#results");
const status = document.querySelector("#status");

// [Implementation 4] 공유 가능한 검색 상태는 별도 메모리가 아니라 현재 URL에서 매번 해석합니다.
function parseLocation() {
  return new URL(location.href).searchParams.get("q")?.trim() ?? "";
}

// [Implementation 5] 신뢰하지 않는 문자열은 textContent로만 DOM에 투영해 markup 실행 경계를 닫습니다.
function render(query) {
  input.value = query;
  const normalized = query.toLocaleLowerCase();
  const filtered = normalized
    ? documents.filter((doc) => `${doc.title} ${doc.body}`.toLocaleLowerCase().includes(normalized))
    : documents;

  results.replaceChildren(...filtered.map((doc) => {
    const article = document.createElement("article");
    article.className = "card";
    const heading = document.createElement("h3");
    heading.textContent = doc.title;
    const body = document.createElement("p");
    body.textContent = doc.body;
    article.append(heading, body);
    return article;
  }));
  status.textContent = `${filtered.length}개 결과`;
}

// [Implementation 6] 제출은 입력을 정규화한 뒤 history에 새 URL 상태를 기록하고 같은 값으로 render합니다.
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  const url = new URL(location.href);
  if (query) url.searchParams.set("q", query);
  else url.searchParams.delete("q");
  history.pushState(null, "", url);
  render(query);
});

// [Implementation 7] history 이동은 오래된 memory snapshot 대신 이동 후 URL을 다시 읽어 화면을 복구합니다.
window.addEventListener("popstate", () => render(parseLocation()));
render(parseLocation());
