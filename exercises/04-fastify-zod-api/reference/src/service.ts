import type { CreateMemoInput } from "./contracts";
import type { MemoRepository } from "./repository";

export class ConflictError extends Error {}

export async function createMemo(repo: MemoRepository, input: CreateMemoInput) {
  if (await repo.findByTitle(input.title)) throw new ConflictError("title_taken");
  return repo.create(input);
}
