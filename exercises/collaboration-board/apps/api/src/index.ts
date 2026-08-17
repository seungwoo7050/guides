import { buildApp } from "./app";
import { loadConfig } from "./config";
import { createMemoryRepository, createPostgresRepository } from "@board/db";

// [Implementation 8] Select and seed the concrete persistence adapter at the executable composition root, then start the only network listener.
const config = loadConfig();
const repo = config.databaseUrl
  ? createPostgresRepository(config.databaseUrl)
  : createMemoryRepository();
await repo.seed();
await buildApp(repo, {
  allowedOrigins: config.allowedOrigins,
  logger: true
}).listen({ host: "0.0.0.0", port: config.port });
