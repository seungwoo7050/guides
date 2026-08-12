import { buildApp } from "./app";
// [Implementation 9] composition root만 실제 listener를 시작해 app factory import와 network resource 생성을 분리합니다.
await buildApp().listen({ host: "0.0.0.0", port: 4000 });
