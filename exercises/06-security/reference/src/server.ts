import { buildApp } from "./app";
await buildApp().listen({ host: "0.0.0.0", port: 4000 });
