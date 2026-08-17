import { readFile } from "node:fs/promises";
import { sql } from "kysely";
import { createDb } from "./db.js";

// [Implementation 3] Own both the SQL source and database resource lifecycle in the migration runner, closing connections on success and failure.
const db = createDb();
try {
  const source = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
  await sql.raw(source).execute(db);
  console.log("migrated");
} finally {
  await db.destroy();
}
