const documents = [
  { id: "runtime", title: "JavaScript runtime", body: "call stack, task, microtask와 취소" },
  { id: "browser", title: "Browser platform", body: "DOM, CSS, accessibility와 history" }
];

const form = document.querySelector("#search-form");
const input = document.querySelector("#query");
const results = document.querySelector("#results");
const status = document.querySelector("#status");

function parseLocation() {
  // TODO: URL에서 `q` 검색 조건을 읽어 주세요.
  return "";
}

function render(query) {
  // TODO: 입력값을 복원하고 검색 결과를 의미에 맞는 `article` 요소로 표시해 주세요.
  status.textContent = "TODO";
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  // TODO: `history.pushState`와 `render`를 호출해 주세요.
});

window.addEventListener("popstate", () => render(parseLocation()));
render(parseLocation());
