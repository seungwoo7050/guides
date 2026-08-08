# PostgreSQL과 Kysely

TypeScript query builder는 열 이름과 결과 형식을 확인하는 데 도움을 주지만, 실제 schema·제약·transaction과 실행 결과를 대신하지 않습니다. Kysely를 사용할 때도 최종 정본은 PostgreSQL이고, TypeScript type은 그 상태를 읽기 위한 컴파일 시점 계약입니다.

## 목표

- PostgreSQL 연결과 pool 수명을 애플리케이션 수명에 맞춥니다.
- Kysely의 database type과 실제 migration schema를 일치시킵니다.
- query builder와 raw SQL의 사용 경계를 설명합니다.
- DB row를 application model·response DTO로 변환합니다.
- 실제 PostgreSQL 통합 검사로 제약과 query를 검증합니다.

## 연결은 pool로 관리합니다

```ts
import { Kysely, PostgresDialect } from "kysely";
import pg from "pg";

const pool = new pg.Pool({
  connectionString: config.databaseUrl,
  max: config.databasePoolSize,
  connectionTimeoutMillis: 5_000
});

export const db = new Kysely<Database>({
  dialect: new PostgresDialect({ pool })
});
```

요청마다 새 pool을 만들지 않습니다. 애플리케이션 시작 시 만들고, 종료 시 새 요청 수락을 멈춘 뒤 진행 중 작업을 정리하고 `db.destroy()`로 연결을 닫습니다.

pool 크기는 무한히 크게 잡지 않습니다. 애플리케이션 instance 수와 PostgreSQL의 허용 connection, query latency를 함께 고려합니다. 연결을 기다리는 시간도 요청 deadline 안에 포함됩니다.

## 환경 변수는 시작 시 검증합니다

```ts
const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  DATABASE_POOL_SIZE: z.coerce.number().int().min(1).max(20).default(5)
});
```

잘못된 URL이나 숫자를 첫 요청 때 발견하지 말고 process 시작 전에 실패시킵니다. 실제 비밀번호를 오류 로그에 그대로 출력하지 않습니다.

## database type은 schema의 복사본이 아닙니다

```ts
interface NoteTable {
  id: string;
  owner_id: string;
  title: string;
  body: string;
  version: number;
  created_at: Date;
  updated_at: Date;
}

interface Database {
  notes: NoteTable;
}
```

실제로는 생성 시 입력할 수 없는 열과 조회 결과 열을 구분하기 위해 `Generated`, `ColumnType` 같은 Kysely type을 사용할 수 있습니다. 중요한 것은 type 정의가 migration과 자동으로 동기화되지 않는다는 점입니다.

다음은 모두 별도 검증이 필요합니다.

```text
migration SQL
↔ Kysely Database type
↔ application mapping
↔ response schema
```

한 곳을 바꿨다고 나머지가 자동으로 맞아지지 않습니다.

## query는 필요한 열만 선택합니다

```ts
const rows = await db
  .selectFrom("notes")
  .select(["id", "title", "version", "updated_at"])
  .where("owner_id", "=", actorId)
  .orderBy("updated_at", "desc")
  .orderBy("id", "desc")
  .limit(limit)
  .execute();
```

`selectAll()`은 편리하지만 password hash, session digest, internal flag 같은 열이 나중에 추가되면 의도치 않게 상위 계층으로 전달될 수 있습니다. 경계별로 필요한 열을 명시합니다.

## row를 application model로 변환합니다

데이터베이스는 snake_case, application은 camelCase를 사용할 수 있습니다.

```ts
function toNote(row: NoteRow): Note {
  return {
    id: row.id,
    ownerId: row.owner_id,
    title: row.title,
    body: row.body,
    version: row.version,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  };
}
```

mapping은 이름만 바꾸는 것이 아니라 DB representation과 domain 의미의 경계입니다. nullable 열, numeric·date representation과 enum 값이 기대 범위인지 확인할 수 있습니다.

## insert와 반환값

```ts
const note = await db
  .insertInto("notes")
  .values({
    id,
    owner_id: ownerId,
    title,
    body,
    version: 0,
    created_at: now,
    updated_at: now
  })
  .returning(["id", "owner_id", "title", "body", "version", "created_at", "updated_at"])
  .executeTakeFirstOrThrow();
```

`executeTakeFirstOrThrow()`는 “반드시 한 행이 생성돼야 한다”는 내부 기대를 표현합니다. 사용자 입력 실패와 DB 연결 실패를 같은 오류로 처리하지 않습니다.

## 낙관적 갱신

```ts
const updated = await db
  .updateTable("notes")
  .set((eb) => ({
    title: input.title,
    version: eb("version", "+", 1),
    updated_at: now
  }))
  .where("id", "=", input.id)
  .where("version", "=", input.baseVersion)
  .returning(["id", "title", "version", "updated_at"])
  .executeTakeFirst();

if (!updated) throw new VersionConflict();
```

먼저 조회하고 나중에 갱신하는 두 문장 사이에는 다른 요청이 끼어들 수 있습니다. 조건부 update 한 문장으로 비교와 쓰기를 묶습니다.

## raw SQL의 경계

Kysely가 표현하기 어려운 PostgreSQL 기능이나 복잡한 query에는 SQL template을 사용할 수 있습니다.

```ts
const result = await sql<{ id: string }>`
  select id
  from notes
  where to_tsvector('simple', title || ' ' || body)
        @@ plainto_tsquery('simple', ${query})
`.execute(db);
```

`${query}`는 parameter로 전달됩니다. `sql.raw(userInput)`으로 사용자 값을 직접 문장에 넣지 않습니다. dynamic identifier가 필요하면 허용 목록에서 선택합니다.

## 오류 번역

PostgreSQL driver error의 code를 adapter 경계에서 해석할 수 있습니다.

```text
23505 unique violation → ConflictError
23503 foreign key violation → InvalidRelationError 또는 conflict
40001 serialization failure → 제한된 안전한 retry 후보
기타 연결·I/O 오류 → infrastructure failure
```

constraint 이름을 안정적으로 지으면 어떤 업무 제약이 실패했는지 더 정확히 번역할 수 있습니다. raw message 전체를 client에 노출하지 않습니다.

## 실제 DB 검사

mock query builder만으로 다음을 증명할 수 없습니다.

- migration SQL이 실제로 적용되는지
- unique·foreign key·check constraint가 작동하는지
- PostgreSQL의 `NULL`, timestamp와 transaction semantics
- 경쟁 update 중 하나만 성공하는지
- rollback 뒤 행이 남지 않는지

실습은 전용 PostgreSQL을 실행하고 각 검사에 고유 식별자를 사용합니다. 검사 뒤 pool과 container를 닫습니다.

## query 관찰

개발 중 느린 query가 있으면 실제 SQL과 parameter, 실행 시간을 관찰하되 비밀값과 개인정보를 가립니다. 성능 판단은 행 수가 거의 없는 개발 DB가 아니라 대표 workload와 `EXPLAIN (ANALYZE, BUFFERS)` 같은 근거를 사용합니다. 깊은 planner·index 학습은 데이터베이스 전문 가이드의 범위입니다.

## 실패 조건

- 요청마다 새 DB pool을 만듭니다.
- 환경 변수를 첫 query에서야 확인합니다.
- Kysely type이 실제 schema를 자동 보장한다고 가정합니다.
- 모든 query에서 `selectAll()`을 사용합니다.
- DB row를 그대로 HTTP 응답으로 보냅니다.
- 사용자 입력을 `sql.raw()`에 넣습니다.
- mock만으로 constraint와 transaction을 검증합니다.

## 연결 실습

[`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)는 전용 PostgreSQL에서 migration, unique 경쟁과 rollback을 검사합니다.

## 완료 기준

- pool의 생성·종료 수명을 애플리케이션 수명과 연결합니다.
- migration, Kysely type, mapping과 response schema의 차이를 설명합니다.
- 필요한 열만 선택하고 row를 application model로 변환합니다.
- 조건부 update와 parameterized raw SQL을 사용할 수 있습니다.
- 실제 PostgreSQL 검사가 필요한 이유를 설명합니다.

## 다음 단계

schema 변화와 여러 쓰기를 원자적으로 적용하는 방법은 [`migration과 transaction`](03-migrations-transactions.md)에서 다룹니다.
