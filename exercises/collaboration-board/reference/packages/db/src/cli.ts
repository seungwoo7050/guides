import { createPostgresRepository } from "./postgres";
import { migrate } from "./migrate";

// [Implementation 3-4]
// migration과 학습용 seed는 server startup의 숨은 부작용이 아니라 명시적으로 실행하는 중간 CLI입니다.
// 각 command가 만든 DB resource는 성공과 실패 모두에서 해당 command가 닫습니다.
const url = process.env.DATABASE_URL;
if (!url) throw new Error("DATABASE_URL이 필요합니다.");
const command = process.argv[2];
if (command === "migrate") await migrate(url);
else if (command === "seed") { const repo = createPostgresRepository(url); try { await repo.seed(); } finally { await repo.close(); } }
else throw new Error("사용법: tsx src/cli.ts migrate|seed");
