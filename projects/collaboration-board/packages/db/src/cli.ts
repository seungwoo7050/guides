import { createPostgresRepository } from "./postgres";
import { migrate } from "./migrate";
const url = process.env.DATABASE_URL;
if (!url) throw new Error("DATABASE_URL이 필요합니다.");
const command = process.argv[2];
if (command === "migrate") await migrate(url);
else if (command === "seed") { const repo = createPostgresRepository(url); try { await repo.seed(); } finally { await repo.close(); } }
else throw new Error("사용법: tsx src/cli.ts migrate|seed");
