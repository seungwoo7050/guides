import { readFile } from "node:fs/promises";
import { Kysely, PostgresDialect, sql } from "kysely";
import { Pool } from "pg";
import type { Database } from "./db-types";

// [Implementation 3-3]
// 적용 여부 기록과 SQL 실행을 같은 transaction에 묶어 부분 적용 상태를 남기지 않습니다.
// 성공·실패 모두에서 Kysely와 pool을 닫는 것까지 migration command의 resource contract입니다.
export async function migrate(url: string) {
  const pool = new Pool({ connectionString: url });
  const db = new Kysely<Database>({ dialect: new PostgresDialect({ pool }) });
  try {
    const version = "001_initial";
    await sql`create table if not exists schema_migrations (version text primary key, applied_at timestamptz not null default now())`.execute(db);
    const applied = await db.selectFrom("schema_migrations").select("version").where("version", "=", version).executeTakeFirst();
    if (!applied) {
      const source = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
      await db.transaction().execute(async (trx) => { await sql.raw(source).execute(trx); await trx.insertInto("schema_migrations").values({ version }).execute(); });
    }
  } finally { await db.destroy(); await pool.end().catch(() => undefined); }
}
