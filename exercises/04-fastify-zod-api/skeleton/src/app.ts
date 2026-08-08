import Fastify from "fastify";
import type { MemoRepository } from "./repository";

export function buildApp(repo: MemoRepository) {
  const app = Fastify({ logger: false });
  // TODO: 목록 조회·단건 조회·생성 라우트를 구현해 주세요.
  // TODO: CreateMemoSchema.safeParse를 사용하고, 400·404·409를 구분하며, 저장소를 주입해 주세요.
  return app;
}
