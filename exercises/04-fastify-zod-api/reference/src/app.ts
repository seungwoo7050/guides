import Fastify from "fastify";
import { CreateMemoSchema } from "./contracts";
import { ConflictError, createMemo } from "./service";
import type { MemoRepository } from "./repository";

export function buildApp(repo: MemoRepository) {
  const app = Fastify({ logger: false });

  app.get("/memos", async () => ({ memos: await repo.list() }));

  app.get("/memos/:id", async (request, reply) => {
    const { id } = request.params as { id: string };
    const memo = await repo.find(id);
    if (!memo) return reply.code(404).send({ code: "not_found", message: "메모를 찾을 수 없습니다." });
    return { memo };
  });

  app.post("/memos", async (request, reply) => {
    const parsed = CreateMemoSchema.safeParse(request.body);
    if (!parsed.success) {
      return reply.code(400).send({ code: "invalid_request", message: "메모 형식이 올바르지 않습니다.", issues: parsed.error.issues });
    }
    try {
      const memo = await createMemo(repo, parsed.data);
      return reply.code(201).send({ memo });
    } catch (error) {
      if (error instanceof ConflictError) return reply.code(409).send({ code: error.message, message: "title already exists" });
      throw error;
    }
  });

  return app;
}
