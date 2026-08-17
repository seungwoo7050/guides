import { buildApp } from "./app.js";
import { MemoryMemoRepository } from "./repository.js";

// [Implementation 7] Select the concrete repository at the executable composition root, then start the network listener.
const app = buildApp(new MemoryMemoRepository());
await app.listen({ host: "0.0.0.0", port: 4000 });
