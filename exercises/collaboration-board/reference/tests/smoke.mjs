import { WebSocket } from "ws";

// [Implementation 8-2]
// 이 짧은 smoke는 HTTP session으로 만든 board를 같은 cookie의 WebSocket이 join해 snapshot을 받는 cross-boundary 증거입니다.
// timeout과 socket close를 명시해 실패한 service나 열린 handle을 성공으로 숨기지 않습니다.
const api = process.env.API_URL ?? "http://localhost:4000";
const handle = `smoke-${Date.now()}`;
const login = await fetch(`${api}/auth/login`, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ handle, displayName: "연결 확인 사용자" })
});
if (!login.ok) throw new Error(`로그인에 실패했습니다: ${login.status}`);
const cookie = login.headers.getSetCookie()[0]?.split(";")[0];
const created = await fetch(`${api}/boards`, {
  method: "POST",
  headers: { "content-type": "application/json", cookie },
  body: JSON.stringify({ title: "연결 확인 보드" })
});
if (!created.ok) throw new Error(`보드를 만들지 못했습니다: ${created.status}`);
const { board } = await created.json();
const socket = new WebSocket(api.replace("http", "ws") + "/ws", {
  headers: { cookie, origin: "http://localhost:3000" }
});
await new Promise((resolve) => socket.once("open", resolve));
const snapshot = new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(new Error("WebSocket 응답 시간이 초과되었습니다.")), 3_000);
  socket.on("message", (raw) => {
    const message = JSON.parse(raw.toString());
    if (message.type === "board.snapshot") {
      clearTimeout(timer);
      resolve(message.snapshot);
    }
  });
});
socket.send(JSON.stringify({ type: "board.join", boardId: board.id }));
const result = await snapshot;
socket.close();
console.log("연결 검사 통과", result.boardId);
