import { buildApp } from "./app";
import { MemoryMemoRepository } from "./repository";
const app = buildApp(new MemoryMemoRepository());
await app.listen({ host: "0.0.0.0", port: 4000 });
