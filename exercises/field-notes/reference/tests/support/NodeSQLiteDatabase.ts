import { DatabaseSync } from "node:sqlite";
import type { SQLiteDatabase } from "expo-sqlite";

function bindings(values: unknown[]): Array<string | number | bigint | Uint8Array | null> {
  const source = values.length === 1 && Array.isArray(values[0])
    ? values[0]
    : values;
  return source.map((value) => {
    if (
      value === null ||
      typeof value === "string" ||
      typeof value === "number" ||
      typeof value === "bigint" ||
      value instanceof Uint8Array
    ) {
      return value;
    }
    throw new TypeError(`unsupported SQLite binding: ${typeof value}`);
  });
}

/** Node 24 adapter for exercising the production SQL path in deterministic Jest tests. */
export class NodeSQLiteDatabase {
  static #memorySequence = 0;
  static readonly #transactionTails = new Map<string, Promise<void>>();
  readonly #database: DatabaseSync;
  readonly #lockKey: string;

  public constructor(filename = ":memory:") {
    this.#database = new DatabaseSync(filename);
    NodeSQLiteDatabase.#memorySequence += 1;
    this.#lockKey = filename === ":memory:"
      ? `memory:${NodeSQLiteDatabase.#memorySequence}`
      : filename;
  }

  public async execAsync(source: string): Promise<void> {
    this.#database.exec(source);
  }

  public async runAsync(source: string, ...values: unknown[]): Promise<{
    changes: number;
    lastInsertRowId: number;
  }> {
    const result = this.#database.prepare(source).run(...bindings(values));
    return {
      changes: Number(result.changes),
      lastInsertRowId: Number(result.lastInsertRowid),
    };
  }

  public async getFirstAsync<T>(source: string, ...values: unknown[]): Promise<T | null> {
    const row = this.#database.prepare(source).get(...bindings(values));
    return row === undefined ? null : ({ ...row } as T);
  }

  public async getAllAsync<T>(source: string, ...values: unknown[]): Promise<T[]> {
    return this.#database
      .prepare(source)
      .all(...bindings(values))
      .map((row) => ({ ...row } as T));
  }

  public async withExclusiveTransactionAsync(
    task: (transaction: SQLiteDatabase) => Promise<void>,
  ): Promise<void> {
    const previous = NodeSQLiteDatabase.#transactionTails.get(this.#lockKey) ?? Promise.resolve();
    let release!: () => void;
    const current = new Promise<void>((resolve) => {
      release = resolve;
    });
    NodeSQLiteDatabase.#transactionTails.set(this.#lockKey, current);
    await previous;
    try {
      this.#database.exec("BEGIN IMMEDIATE");
      try {
        await task(this.asExpoDatabase());
        this.#database.exec("COMMIT");
      } catch (error) {
        this.#database.exec("ROLLBACK");
        throw error;
      }
    } finally {
      release();
      if (NodeSQLiteDatabase.#transactionTails.get(this.#lockKey) === current) {
        NodeSQLiteDatabase.#transactionTails.delete(this.#lockKey);
      }
    }
  }

  public asExpoDatabase(): SQLiteDatabase {
    return this as unknown as SQLiteDatabase;
  }

  public close(): void {
    this.#database.close();
  }
}
