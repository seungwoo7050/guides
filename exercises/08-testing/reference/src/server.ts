import { buildApp } from "./app";
// [Implementation 5] executable entry가 test별 고유 port를 읽고 실제 network listener의 수명을 시작합니다.
await buildApp().listen({
  host: "127.0.0.1",
  port: Number(process.env.EXERCISE_PORT ?? "4100")
});
