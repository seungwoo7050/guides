import Fastify from "fastify";

import { reduceCounter, type CounterAction } from "./counter";

const ACTIONS: CounterAction["type"][] = ["increment", "decrement", "reset"];

// [Implementation 3] Give each app instance ownership of one counter and connect the pure transition to HTTP and an accessible browser projection.
export function buildApp() {
  const app = Fastify({ logger: false });
  let value = 0;

  app.get("/", async (_request, reply) => reply.type("text/html; charset=utf-8").send(renderPage(value)));
  app.get("/counter", async () => ({ value }));

  for (const action of ACTIONS) {
    app.post(`/counter/${action}`, async () => {
      value = reduceCounter(value, { type: action });
      return { value };
    });
  }

  return app;
}

function renderPage(value: number): string {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Counter Quality Suite</title>
  <style>
    :root { font-family: system-ui, sans-serif; color: #172033; background: #f5f7fb; }
    body { margin: 0; }
    main { width: min(32rem, calc(100% - 2rem)); margin: 3rem auto; padding: 2rem; border-radius: 1rem; background: white; }
    #value { font-size: 3rem; font-variant-numeric: tabular-nums; }
    .actions { display: flex; flex-wrap: wrap; gap: .75rem; }
    button { padding: .7rem 1rem; font: inherit; }
    :focus-visible { outline: 3px solid #f59e0b; outline-offset: 3px; }
  </style>
</head>
<body>
  <main>
    <h1>Counter</h1>
    <p id="value" role="status" aria-live="polite">${value}</p>
    <div class="actions">
      <button type="button" data-action="increment">Increment</button>
      <button type="button" data-action="decrement">Decrement</button>
      <button type="button" data-action="reset">Reset</button>
    </div>
    <p id="error" role="alert"></p>
  </main>
  <script type="module">
    document.querySelector('.actions').addEventListener('click', async (event) => {
      const button = event.target.closest('button[data-action]');
      if (!button) return;
      const error = document.querySelector('#error');
      error.textContent = '';
      try {
        const response = await fetch('/counter/' + button.dataset.action, { method: 'POST' });
        if (!response.ok) throw new Error('counter request failed');
        const data = await response.json();
        document.querySelector('#value').textContent = String(data.value);
      } catch {
        error.textContent = 'The counter could not be updated.';
      }
    });
  </script>
</body>
</html>`;
}
