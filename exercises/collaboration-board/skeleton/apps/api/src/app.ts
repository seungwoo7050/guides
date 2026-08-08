import type { HealthResponse } from "@capstone/contracts";
import { createMemoryRepository, type ApplicationRepository } from "@capstone/db";
import Fastify, { type FastifyInstance } from "fastify";

export function buildApp(repository: ApplicationRepository = createMemoryRepository()): FastifyInstance {
  const app = Fastify({ logger: true });

  app.get("/health", async (): Promise<HealthResponse> => ({ status: "ok" }));
  app.addHook("onClose", async () => repository.close());

  return app;
}

export function createApplication(repository: ApplicationRepository = createMemoryRepository()) {
  const app = buildApp(repository);
  let closing: Promise<void> | undefined;

  return {
    app,
    close() {
      closing ??= app.close();
      return closing;
    }
  };
}
