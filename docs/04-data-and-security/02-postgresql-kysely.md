# PostgreSQL과 Kysely

TypeScript 쿼리 빌더는 열 이름과 결과 타입을 확인하는 데 도움을 주지만 실제 스키마, 제약 조건, 트랜잭션, 실행 결과를 대신하지는 않습니다. Kysely를 사용하더라도 데이터의 기준은 PostgreSQL에 있으며, TypeScript 타입은 그 데이터를 다루기 위한 컴파일 시점의 보조 수단입니다.

## 목표

- PostgreSQL 연결 풀의 수명을 애플리케이션 수명에 맞춥니다.
- Kysely의 데이터베이스 타입과 실제 마이그레이션 스키마를 일치시킵니다.
- 쿼리 빌더와 원시 SQL을 사용할 경계를 설명합니다.
- 데이터베이스 행을 애플리케이션 모델과 응답 DTO로 변환합니다.
- 실제 PostgreSQL 통합 테스트로 제약 조건과 쿼리를 검증합니다.

## 연결은 풀로 관리합니다

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

요청마다 새 연결 풀을 만들지 않습니다. 애플리케이션이 시작될 때 한 번 생성하고, 종료할 때는 새 요청 수락을 중단한 뒤 진행 중인 작업을 정리하고 `db.destroy()`로 연결을 닫습니다.

풀 크기를 무조건 크게 잡아서도 안 됩니다. 애플리케이션 인스턴스 수, PostgreSQL이 허용하는 연결 수, 쿼리 지연 시간을 함께 고려합니다. 연결을 기다리는 시간도 요청 제한 시간에 포함됩니다.

## 환경 변수는 시작할 때 검증합니다

```ts
const EnvSchema = z.object({
  DATABASE_URL: z.string().url(),
  DATABASE_POOL_SIZE: z.coerce.number().int().min(1).max(20).default(5)
});
```

잘못된 URL이나 숫자를 첫 요청에서 발견하지 말고 프로세스가 시작되기 전에 검증합니다. 오류 로그에 실제 비밀번호를 그대로 출력해서는 안 됩니다.

## 데이터베이스 타입은 스키마의 자동 복사본이 아닙니다

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

실제 코드에서는 삽입할 때 지정할 수 없는 열과 조회 결과의 열을 구분하기 위해 `Generated`, `ColumnType` 같은 Kysely 타입을 사용할 수 있습니다. 중요한 점은 이 타입 정의가 마이그레이션과 자동으로 동기화되지 않는다는 것입니다.

다음 네 요소는 각각 검증해야 합니다.

```text
마이그레이션 SQL
↔ Kysely Database 타입
↔ 애플리케이션 매핑
↔ 응답 스키마
```

한 곳을 변경해도 나머지가 자동으로 맞춰지지 않습니다.

## 쿼리는 필요한 열만 선택합니다

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

`selectAll()`은 편리하지만 이후 비밀번호 해시, 세션 다이제스트, 내부 플래그 같은 열이 추가되면 의도치 않게 상위 계층으로 전달될 수 있습니다. 각 경계에서 필요한 열만 명시합니다.

## 행을 애플리케이션 모델로 변환합니다

데이터베이스에는 `snake_case`, 애플리케이션에는 `camelCase`를 사용할 수 있습니다.

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

매핑은 필드 이름만 바꾸는 작업이 아닙니다. 데이터베이스 표현과 도메인 의미를 분리하는 경계이며, nullable 열, 숫자·날짜 표현, 열거형 값이 애플리케이션에서 기대하는 범위에 있는지도 이곳에서 확인할 수 있습니다.

## INSERT와 반환값

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

`executeTakeFirstOrThrow()`는 이 작업에서 반드시 한 행이 생성되어야 한다는 내부 전제를 표현합니다. 사용자 입력 오류와 데이터베이스 연결 오류를 같은 종류의 오류로 처리해서는 안 됩니다.

## 낙관적 동시성 제어

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

먼저 조회한 뒤 나중에 갱신하는 두 쿼리 사이에는 다른 요청이 끼어들 수 있습니다. 조건부 `UPDATE` 한 문장으로 버전 비교와 쓰기를 함께 처리합니다.

## 원시 SQL을 사용할 경계

Kysely로 표현하기 어려운 PostgreSQL 기능이나 복잡한 쿼리에는 SQL 템플릿을 사용할 수 있습니다.

```ts
const result = await sql<{ id: string }>`
  select id
  from notes
  where to_tsvector('simple', title || ' ' || body)
        @@ plainto_tsquery('simple', ${query})
`.execute(db);
```

`${query}`는 쿼리 매개변수로 전달됩니다. 사용자 입력을 `sql.raw(userInput)`으로 직접 SQL 문장에 넣지 않습니다. 동적인 식별자가 필요하면 미리 정한 허용 목록에서만 선택합니다.

## 오류 변환

PostgreSQL 드라이버 오류 코드는 어댑터 경계에서 애플리케이션 오류로 변환할 수 있습니다.

```text
23505 unique violation → ConflictError
23503 foreign key violation → InvalidRelationError 또는 conflict
40001 serialization failure → 제한적으로 재시도할 수 있는 오류
기타 연결·I/O 오류 → 인프라 오류
```

제약 조건에 안정적인 이름을 지정하면 어떤 도메인 제약이 실패했는지 더 정확히 판단할 수 있습니다. 원본 오류 메시지 전체를 클라이언트에 노출해서는 안 됩니다.

## 실제 데이터베이스 테스트

쿼리 빌더를 모킹하는 것만으로는 다음 항목을 증명할 수 없습니다.

- 마이그레이션 SQL이 실제로 적용되는지
- 고유·외래 키·검사 제약 조건이 동작하는지
- PostgreSQL의 `NULL`, 타임스탬프, 트랜잭션 동작
- 경쟁하는 갱신 중 하나만 성공하는지
- 롤백 후 행이 남지 않는지

실습에서는 전용 PostgreSQL을 실행하고 각 테스트에 고유한 식별자를 사용합니다. 테스트가 끝나면 연결 풀과 컨테이너를 종료합니다.

## 쿼리 관찰

개발 중 느린 쿼리가 있다면 실제 SQL, 매개변수, 실행 시간을 확인하되 비밀값과 개인정보는 마스킹합니다. 성능은 행이 거의 없는 개발 데이터베이스가 아니라 대표적인 작업 부하와 `EXPLAIN (ANALYZE, BUFFERS)` 같은 근거로 판단합니다. 쿼리 플래너와 인덱스의 세부 내용은 데이터베이스 전문 가이드의 범위입니다.

## 흔한 오류

- 요청마다 새 데이터베이스 연결 풀을 만듭니다.
- 환경 변수를 첫 쿼리에서야 검증합니다.
- Kysely 타입이 실제 스키마를 자동으로 보장한다고 가정합니다.
- 모든 쿼리에서 `selectAll()`을 사용합니다.
- 데이터베이스 행을 그대로 HTTP 응답으로 보냅니다.
- 사용자 입력을 `sql.raw()`에 넣습니다.
- 모킹만으로 제약 조건과 트랜잭션을 검증합니다.

## 연결 실습

[`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)는 전용 PostgreSQL에서 마이그레이션, 고유성 경쟁, 롤백을 검사합니다.

## 완료 기준

- 연결 풀의 생성과 종료를 애플리케이션 수명에 맞춥니다.
- 마이그레이션, Kysely 타입, 애플리케이션 매핑, 응답 스키마의 차이를 설명할 수 있습니다.
- 필요한 열만 선택하고 행을 애플리케이션 모델로 변환합니다.
- 조건부 `UPDATE`와 매개변수화된 원시 SQL을 사용할 수 있습니다.
- 실제 PostgreSQL 테스트가 필요한 이유를 설명할 수 있습니다.

## 다음 단계

스키마 변경과 여러 쓰기를 원자적으로 적용하는 방법은 [`마이그레이션과 트랜잭션`](03-migrations-transactions.md)에서 다룹니다.
