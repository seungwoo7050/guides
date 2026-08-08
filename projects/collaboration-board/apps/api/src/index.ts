import { createMemoryRepository, createPostgresRepository } from "@board/db";
import { buildApp } from "./app";

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
