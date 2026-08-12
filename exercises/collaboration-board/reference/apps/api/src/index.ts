import { createMemoryRepository, createPostgresRepository } from "@board/db";
import { buildApp } from "./app";

// [Implementation 5-5]
// composition root만 환경 변수로 adapter를 선택하고 seed·origin·listen을 연결합니다.
// app factory와 repository는 import 시 process를 시작하지 않아 test와 production이 같은 계약을 재사용합니다.
const repo = process.env.DATABASE_URL
  ? createPostgresRepository(process.env.DATABASE_URL)
  : createMemoryRepository();
await repo.seed();
const allowedOrigins = (process.env.WEB_ORIGINS ?? "http://localhost:3000,http://localhost:8080")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);
const app = buildApp(repo, { allowedOrigins });
await app.listen({ host: "0.0.0.0", port: Number(process.env.PORT ?? 4000) });
