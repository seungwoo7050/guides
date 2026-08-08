import { buildApp } from "./app";
await buildApp().listen({
  host: "127.0.0.1",
  port: Number(process.env.EXERCISE_PORT ?? "4100")
});
