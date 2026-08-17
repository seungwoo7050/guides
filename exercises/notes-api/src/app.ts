import Fastify, { type FastifyError } from "fastify";
import { CreateMemoSchema } from "./contracts.js";
import { ConflictError, createMemo } from "./service.js";
import type { MemoRepository } from "./repository.js";

// [Implementation 4] Inject the repository through an app factory so tests isolate state and unexpected failures close behind a stable response contract.
export function buildApp(repo: MemoRepository) {
  const app = Fastify({ logger: false });

  app.setErrorHandler((error: FastifyError, _request, reply) => {
    if (error.statusCode && error.statusCode >= 400 && error.statusCode < 500) {
      return reply.code(error.statusCode).send({
        code: "invalid_request",
        message: "The request is invalid."
      });
    }
    return reply.code(500).send({
      code: "internal_error",
      message: "The request could not be processed."
    });
  });

  // [Implementation 5] Map HTTP parameters and repository results at read routes, distinguishing resource absence with a stable 404 response.
  app.get("/memos", async () => ({ memos: await repo.list() }));

  app.get("/memos/:id", async (request, reply) => {
    const { id } = request.params as { id: string };
    const memo = await repo.find(id);
    if (!memo) {
      return reply.code(404).send({
        code: "not_found",
        message: "Memo not found."
      });
    }
    return { memo };
  });

  // [Implementation 6] Coordinate body parsing, service execution, and the expected conflict-to-409 translation at the write route.
  app.post("/memos", async (request, reply) => {
    const parsed = CreateMemoSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.code(400).send({
        code: "invalid_request",
        message: "The request is invalid."
      });
    }
    try {
      const memo = await createMemo(repo, parsed.data);
      return reply.code(201).send({ memo });
    } catch (error) {
      if (error instanceof ConflictError) {
        return reply.code(409).send({
          code: error.message,
          message: "title already exists"
        });
      }
      throw error;
    }
  });

  return app;
}
