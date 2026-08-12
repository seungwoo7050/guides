import Fastify from "fastify";
import { reduceCounter } from "./counter";

// [Implementation 3] app factory가 순수 transition을 HTTP route와 접근 가능한 HTML projection에 연결합니다.
export function buildApp() {
  const app = Fastify({ logger: false });
  let value = 0;
  app.get("/", async (_request, reply) => reply.type("text/html").send(`<!doctype html><html lang="ko"><head><meta charset="utf-8"></head><body><main><h1>Counter</h1><p id="value" role="status">${value}</p><button id="increment">증가</button><button id="decrement">감소</button><script>for(const action of ['increment','decrement'])document.querySelector('#'+action).onclick=async()=>{const r=await fetch('/counter/'+action,{method:'POST'});const d=await r.json();document.querySelector('#value').textContent=d.value}</script></main></body></html>`));
  app.get("/counter", async () => ({ value }));
  app.post("/counter/increment", async () => ({ value: value = reduceCounter(value, { type: "increment" }) }));
  app.post("/counter/decrement", async () => ({ value: value = reduceCounter(value, { type: "decrement" }) }));
  return app;
}
