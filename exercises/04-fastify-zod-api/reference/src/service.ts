import type { CreateMemoInput } from "./contracts";
import type { MemoRepository } from "./repository";

// [Implementation 3] 제목 중복은 transport가 아니라 use-case invariant이므로 service가 안정된 domain failure로 표현합니다.
export class ConflictError extends Error {}

export async function createMemo(repo: MemoRepository, input: CreateMemoInput) {
  if (await repo.findByTitle(input.title)) throw new ConflictError("title_taken");
  return repo.create(input);
}
