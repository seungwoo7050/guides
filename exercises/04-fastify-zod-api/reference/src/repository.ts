import { randomUUID } from "node:crypto";
import type { CreateMemoInput, Memo } from "./contracts";

// [Implementation 2] 저장 port가 service의 의존 경계를 정하고 각 repository instance가 자신의 row 수명을 소유합니다.
export interface MemoRepository {
  list(): Promise<Memo[]>;
  find(id: string): Promise<Memo | null>;
  findByTitle(title: string): Promise<Memo | null>;
  create(input: CreateMemoInput): Promise<Memo>;
}

export class MemoryMemoRepository implements MemoRepository {
  private readonly rows = new Map<string, Memo>();
  async list() { return [...this.rows.values()]; }
  async find(id: string) { return this.rows.get(id) ?? null; }
  async findByTitle(title: string) { return [...this.rows.values()].find((row) => row.title === title) ?? null; }
  async create(input: CreateMemoInput) {
    const row = { id: randomUUID(), ...input };
    this.rows.set(row.id, row);
    return row;
  }
}
