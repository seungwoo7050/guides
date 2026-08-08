# Capstone 2: 메모 API

두 번째 프로젝트는 화면을 제외하고 HTTP API와 PostgreSQL에 집중합니다. Fastify route, Zod 전송 계약, application service, Kysely repository와 실제 transaction을 연결해 **한 요청이 어디서 검증되고 어떤 상태를 남기는지** 추적합니다.

## 목표

다음 API를 구현합니다.

```text
GET    /health
GET    /notes
POST   /notes
GET    /notes/:id
PATCH  /notes/:id
DELETE /notes/:id
GET    /notes/:id/activity
```

이 단계에는 로그인 대신 고정된 개발 actor를 application composition에서 주입할 수 있습니다. 인증을 생략하더라도 route가 owner ID를 client body에서 신뢰하지 않게 합니다.

연결 실습:

- [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)
- [`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)

두 실습의 reference를 복사해 합치는 것이 아니라, 이 문서의 계약을 보고 새 디렉터리에서 직접 조립합니다.

## 데이터 모델

```text
notes
- id
- owner_id
- title
- body
- version
- created_at
- updated_at
- archived_at (nullable)

note_activity
- id
- note_id
- actor_id
- action
- note_version
- created_at
```

필수 제약:

- 모든 primary key
- `notes.owner_id → users.id`, `note_activity.note_id → notes.id`, `note_activity.actor_id → users.id` 외래 키
- 제목 trim 후 1~120자
- version 0 이상
- activity action 허용 목록
- `(note_id, note_version, action)` 또는 제품 계약에 맞는 중복 방지

activity 구조는 단순 감사 예제입니다. event sourcing으로 사용하지 않습니다.

## HTTP 계약

### 생성

```http
POST /notes
Content-Type: application/json

{
  "title": "회의 기록",
  "body": "결정 사항"
}
```

성공은 `201 Created`와 공개 DTO를 반환합니다. 잘못된 JSON·빈 제목·길이 초과는 400입니다.

### 수정

```http
PATCH /notes/{id}

{
  "title": "수정된 제목",
  "body": "새 내용",
  "baseVersion": 2
}
```

- 자원 없음: 404
- version 충돌: 409
- 성공: version 3의 DTO

update와 activity insert는 한 transaction으로 성공해야 합니다.

### 삭제

물리 삭제 또는 archive 중 하나를 선택하고 계약을 문서화합니다. 이 capstone 기본안은 `archived_at`을 두는 보관 방식을 사용해 activity를 유지할 수 있습니다. 보관된 메모는 일반 목록에서 빠지고 수정할 수 없습니다.

## 디렉터리 구조

```text
src/
├── config.ts
├── app.ts
├── server.ts
├── domain/
│   ├── note.ts
│   └── errors.ts
├── application/
│   └── note-service.ts
├── http/
│   ├── schemas.ts
│   ├── note-routes.ts
│   └── error-handler.ts
└── persistence/
    ├── database.ts
    ├── note-repository.ts
    └── migrations/
```

파일 수 자체가 목표는 아닙니다. route·업무 조정·DB adapter·composition의 의존 방향을 보이게 합니다.

## App factory

```ts
export async function buildApp(dependencies?: Partial<Dependencies>) {
  const app = Fastify({ logger: true });
  const deps = createDependencies(dependencies);
  await app.register(noteRoutes, { service: deps.noteService });
  app.setErrorHandler(createErrorHandler());
  app.addHook("onClose", async () => deps.close());
  await app.ready();
  return app;
}
```

검사는 실제 port 없이 `app.inject`를 사용하고, production entrypoint만 `listen`합니다.

## 오류 계약

```json
{
  "code": "stale_note",
  "message": "다른 변경이 먼저 저장되었습니다.",
  "requestId": "req-..."
}
```

client가 의존할 안정된 `code`와 사용자 message를 구분할 수 있습니다. validation detail은 허용된 field path만 제공합니다. DB 오류·stack·SQL을 노출하지 않습니다.

## Transaction

수정 use case:

```text
조건부 note update(version 일치)
→ 실패하면 409
→ activity insert
→ 둘 다 commit
→ DTO 반환
```

activity insert 전에 의도적으로 예외를 발생시키는 검사로 note update도 rollback되는지 확인합니다.

## Migration

- 빈 PostgreSQL에 전체 migration 적용
- 두 번째 실행의 정책 확인
- application 시작과 migration 명령 분리
- schema type과 Kysely `Database` type 일치
- test DB마다 깨끗한 schema 또는 고유 database 사용

제공된 Compose 파일로 전용 PostgreSQL을 실행할 수 있습니다.

## 검사 목록

### 단위

- title normalization
- archived note 수정 거부
- version 증가 계산

### API

- 생성 201
- validation 400
- 없는 note 404
- stale update 409
- 내부 오류 500과 detail 비노출
- stable pagination order

### DB

- migration
- constraint
- 수정+activity rollback
- 같은 version의 동시 update 중 하나만 성공
- pool cleanup

## 구현 순서

1. request·response schema와 error code를 먼저 적습니다.
2. 메모리 repository로 route·service 흐름을 통과시킵니다.
3. migration과 Kysely type을 작성합니다.
4. PostgreSQL repository를 연결합니다.
5. transaction·concurrency 검사를 추가합니다.
6. production server entrypoint와 shutdown을 연결합니다.
7. typecheck·test를 깨끗한 DB에서 반복합니다.

## 범위 밖

- 로그인·cookie
- 여러 사용자 공유
- React 화면
- WebSocket
- 고급 검색·전문 index tuning
- Docker production 배포

이 제한 덕분에 API와 DB 경계를 독립적으로 완성할 수 있습니다.

## 완료 기준

- Fastify app factory와 server entrypoint를 분리합니다.
- 모든 외부 입력과 response를 runtime schema로 검증합니다.
- route·service·repository 책임과 error translation을 설명합니다.
- 실제 PostgreSQL에서 migration·constraint·rollback·경쟁을 검사합니다.
- 프로세스 종료 시 server와 DB pool을 닫습니다.

## 다음 단계

React 화면, 사용자 session과 자원별 권한을 결합하는 세 번째 프로젝트는 [`공유 메모`](03-shared-notes.md)입니다.
