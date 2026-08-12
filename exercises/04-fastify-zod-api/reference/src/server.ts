import { buildApp } from "./app";
import { MemoryMemoRepository } from "./repository";
// [Implementation 7] executable composition root에서 concrete repository를 선택한 뒤 network listener를 시작합니다.
const app = buildApp(new MemoryMemoRepository());
await app.listen({ host: "0.0.0.0", port: 4000 });
