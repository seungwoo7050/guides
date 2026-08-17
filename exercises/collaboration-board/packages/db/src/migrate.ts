import { readFile } from "node:fs/promises";

import { Kysely, PostgresDialect, sql } from "kysely";
import { Pool } from "pg";

import type { Database } from "./db-types";

const connectionString = process.env.DATABASE_URL;
if (!connectionString) throw new Error("DATABASE_URL is required");

const pool = new Pool({ connectionString });
const db = new Kysely<Database>({ dialect: new PostgresDialect({ pool }) });
try {
  const source = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
  await sql.raw(source).execute(db);
  await db.insertInto("schema_migrations")
    .values({ version: "001_initial" })
    .onConflict((conflict) => conflict.column("version").doNothing())
    .execute();
  console.log("Applied migration 001_initial");
} finally {
  await db.destroy();
}
