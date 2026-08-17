import { readFile } from "node:fs/promises";
import { sql } from "kysely";
import { loadConfig } from "./config.js";
import { createDatabase } from "./db.js";

const config = loadConfig(process.env);
const db = createDatabase(config.DATABASE_URL);
try {
  const source = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
  await sql.raw(source).execute(db);
  console.log("migration applied");
} finally {
  await db.destroy();
}
