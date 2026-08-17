// [Implementation 3] Own the static search corpus and DOM handles in one module to define the projection input boundary.
const documents = [
  { id: "runtime", title: "JavaScript runtime", body: "call stack, tasks, microtasks, and cancellation" },
  { id: "browser", title: "Browser platform", body: "DOM, CSS, accessibility, and history" },
  { id: "api", title: "HTTP API", body: "runtime validation and error contracts" },
  { id: "realtime", title: "Realtime state", body: "WebSocket room, snapshot, reconnect" }
];

const form = document.querySelector("#search-form");
const input = document.querySelector("#query");
const results = document.querySelector("#results");
const status = document.querySelector("#status");

// [Implementation 4] Derive shareable search state from the current URL instead of maintaining a competing in-memory source of truth.
function parseLocation() {
  return new URL(location.href).searchParams.get("q")?.trim() ?? "";
}

// [Implementation 5] Project untrusted strings through textContent only so search data cannot cross the markup execution boundary.
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
  status.textContent = `${filtered.length} results`;
}

// [Implementation 6] Normalize submitted input, commit the new URL state to history, and render from the same value.
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = input.value.trim();
  const url = new URL(location.href);
  if (query) url.searchParams.set("q", query);
  else url.searchParams.delete("q");
  history.pushState(null, "", url);
  render(query);
});

// [Implementation 7] Recover history navigation by reparsing the destination URL instead of replaying stale memory.
window.addEventListener("popstate", () => render(parseLocation()));
render(parseLocation());
