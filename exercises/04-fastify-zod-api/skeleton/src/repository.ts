import { randomUUID } from "node:crypto";
import type { CreateMemoInput, Memo } from "./contracts";

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
