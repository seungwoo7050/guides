import { readFile } from "node:fs/promises";
import { sql } from "kysely";
import { createDb } from "./db";
const { db, pool } = createDb();
try {
  const source = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
  await sql.raw(source).execute(db);
  console.log("migrated");
} finally {
  await db.destroy();
  await pool.end().catch(() => undefined);
}
