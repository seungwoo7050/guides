// [Implementation 3] Make the task collection and URL filter the owners of application state, then perform the first DOM projection.
const STORAGE_KEY = "task-list.tasks.v1";
const allowedFilters = new Set(["all", "open", "done"]);

const form = document.querySelector("#task-form");
const titleInput = document.querySelector("#task-title");
const filterInput = document.querySelector("#filter");
const list = document.querySelector("#task-list");
const error = document.querySelector("#error");
const status = document.querySelector("#status");

let tasks = readTasks();
let filter = readFilter();
filterInput.value = filter;
render();

// [Implementation 4] Normalize input at the submission boundary, reject empty titles, and append through immutable state replacement.
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = titleInput.value.trim();
  if (!title) {
    error.textContent = "Enter a task description.";
    titleInput.focus();
    return;
  }
  error.textContent = "";
  tasks = [...tasks, { id: crypto.randomUUID(), title, completed: false }];
  titleInput.value = "";
  persist();
  render();
});

filterInput.addEventListener("change", () => {
  const next = allowedFilters.has(filterInput.value) ? filterInput.value : "all";
  const url = new URL(location.href);
  if (next === "all") url.searchParams.delete("filter");
  else url.searchParams.set("filter", next);
  history.pushState(null, "", url);
  filter = next;
  render();
});

window.addEventListener("popstate", () => {
  filter = readFilter();
  filterInput.value = filter;
  render();
});

// [Implementation 5] Delegate list mutations through one event boundary and keep rendering as the only DOM projection path.
list.addEventListener("change", (event) => {
  const checkbox = event.target.closest('input[type="checkbox"][data-task-id]');
  if (!checkbox) return;
  tasks = tasks.map((task) => task.id === checkbox.dataset.taskId
    ? { ...task, completed: checkbox.checked }
    : task);
  persist();
  render();
});

list.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-task-id]");
  if (!button) return;
  tasks = tasks.filter((task) => task.id !== button.dataset.taskId);
  persist();
  render();
});

function render() {
  const visible = tasks.filter((task) => {
    if (filter === "open") return !task.completed;
    if (filter === "done") return task.completed;
    return true;
  });
  list.replaceChildren(...visible.map((task) => {
    const item = document.createElement("li");
    item.className = "task";
    item.dataset.completed = String(task.completed);

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = task.completed;
    checkbox.dataset.taskId = task.id;
    checkbox.setAttribute("aria-label", `${task.title} completed`);

    const title = document.createElement("span");
    title.textContent = task.title;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.dataset.taskId = task.id;
    remove.textContent = "Delete";
    remove.setAttribute("aria-label", `Delete ${task.title}`);

    item.append(checkbox, title, remove);
    return item;
  }));
  const open = tasks.filter((task) => !task.completed).length;
  status.textContent = `Total ${tasks.length}, open ${open}`;
}

// [Implementation 6] Revalidate persisted input and treat the URL as the filter source of truth across reload and history navigation.
function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

function readTasks() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isTask).map((task) => ({
      id: task.id,
      title: task.title.trim(),
      completed: task.completed
    }));
  } catch {
    return [];
  }
}

function isTask(value) {
  return typeof value === "object" && value !== null
    && typeof value.id === "string" && value.id.length > 0
    && typeof value.title === "string" && value.title.trim().length > 0
    && typeof value.completed === "boolean";
}

function readFilter() {
  const value = new URL(location.href).searchParams.get("filter") ?? "all";
  return allowedFilters.has(value) ? value : "all";
}
