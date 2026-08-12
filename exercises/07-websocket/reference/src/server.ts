import { buildApp } from "./app";
// [Implementation 9] executable composition root에서 비동기 app 구성을 마친 뒤 network listener를 시작합니다.
const app = await buildApp();
await app.listen({ host: "0.0.0.0", port: 4000 });
