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

function parseLocation() {
  return new URL(location.href).searchParams.get("q")?.trim() ?? "";
}

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

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  const url = new URL(location.href);
  if (query) url.searchParams.set("q", query);
  else url.searchParams.delete("q");
  history.pushState(null, "", url);
  render(query);
});

window.addEventListener("popstate", () => render(parseLocation()));
render(parseLocation());
