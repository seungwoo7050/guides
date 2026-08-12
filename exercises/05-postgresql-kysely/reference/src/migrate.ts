import { readFile } from "node:fs/promises";
import { sql } from "kysely";
import { createDb } from "./db";
// [Implementation 3] migration runner가 SQL source와 DB resource의 수명을 소유해 성공·실패 모두 connection을 닫습니다.
const { db, pool } = createDb();
try {
  const source = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
  await sql.raw(source).execute(db);
  console.log("migrated");
} finally {
  await db.destroy();
  await pool.end().catch(() => undefined);
}
