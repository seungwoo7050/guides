import Fastify from "fastify";
import { reduceCounter } from "./counter";

export function buildApp() {
  const app = Fastify({ logger: false });
  let value = 0;
  app.get("/", async (_request, reply) => reply.type("text/html").send(`<!doctype html><html lang="ko"><head><meta charset="utf-8"></head><body><main><h1>Counter</h1><p id="value" role="status">${value}</p><button id="increment">증가</button><script>document.querySelector('#increment').onclick=async()=>{const r=await fetch('/counter/increment',{method:'POST'});const d=await r.json();document.querySelector('#value').textContent=d.value}</script></main></body></html>`));
  app.get("/counter", async () => ({ value }));
  app.post("/counter/increment", async () => ({ value: value = reduceCounter(value, { type: "increment" }) }));
  return app;
}
