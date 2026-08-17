# 종합 프로젝트 2: 메모 API

두 번째 프로젝트는 화면을 제외하고 HTTP API와 PostgreSQL에 집중합니다. Fastify 라우트, Zod 전송 계약, 애플리케이션 서비스, Kysely 리포지터리, 실제 트랜잭션을 연결해 **한 요청이 어느 경계에서 검증되고 어떤 상태를 남기는지** 추적합니다.

> **과제 형식:** 데이터베이스 실습 이후 선택해서 수행하는 증거 기반 자율 과제입니다. 저장소에는 이 과제 전용 `skeleton/`, Compose 구성, 자동 검증기, 참조 구현이 없습니다. `04-fastify-zod-api`와 `05-postgresql-kysely`를 통과한 뒤 저장소 밖에 새 프로젝트를 만들어 구현하고, 아래의 완료 증거 기준으로 직접 검토합니다.

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

이 단계에서는 로그인 대신 애플리케이션 조립 코드에서 고정된 개발 사용자 문맥을 주입할 수 있습니다. 인증을 생략하더라도 라우트가 클라이언트 본문의 소유자 ID를 신뢰해서는 안 됩니다.

연결 실습:

- [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)
- [`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)

두 실습의 참조 구현을 그대로 합치지 말고 이 문서의 요구사항을 바탕으로 별도 디렉터리에서 직접 조립합니다. 디렉터리 위치, 패키지 관리자, Git 이력은 학습자가 관리하며 `guides`의 검증기는 해당 경로를 읽거나 변경하지 않습니다.

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

필수 제약 조건:

- 모든 테이블의 기본 키
- `notes.owner_id → users.id`, `note_activity.note_id → notes.id`, `note_activity.actor_id → users.id` 외래 키
- 앞뒤 공백을 제거한 제목이 1~120자
- 버전이 0 이상
- 허용된 활동 유형만 저장
- `(note_id, note_version, action)` 또는 제품 요구사항에 맞는 중복 방지 제약

활동 테이블은 간단한 감사 기록 예제입니다. 이벤트 소싱의 원장으로 사용하지 않습니다.

## HTTP 요구사항

### 생성

```http
POST /notes
Content-Type: application/json

{
  "title": "회의 기록",
  "body": "결정 사항"
}
```

성공하면 `201 Created`와 공개 가능한 DTO를 반환합니다. 잘못된 JSON, 빈 제목, 길이 초과는 400으로 처리합니다.

### 수정

```http
PATCH /notes/{id}

{
  "title": "수정된 제목",
  "body": "새 내용",
  "baseVersion": 2
}
```

- 리소스 없음: 404
- 버전 충돌: 409
- 성공: 버전 3인 DTO 반환

메모 갱신과 활동 기록 삽입은 하나의 트랜잭션에서 함께 성공해야 합니다.

### 삭제 또는 보관

물리 삭제와 보관 중 하나를 선택하고 외부 동작을 문서화합니다. 기본 설계는 `archived_at`을 사용하는 보관 방식으로 활동 기록을 유지합니다. 보관된 메모는 일반 목록에서 제외하고 더 이상 수정할 수 없게 합니다.

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

파일 수 자체는 목표가 아닙니다. 라우트, 도메인 작업 조정, 데이터베이스 어댑터, 의존성 조립의 방향이 드러나야 합니다.

## 애플리케이션 팩터리

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

테스트에서는 실제 포트를 열지 않고 `app.inject`를 사용합니다. 프로덕션 진입점에서만 `listen`을 호출합니다.

## 오류 응답

```json
{
  "code": "stale_note",
  "message": "다른 변경이 먼저 저장되었습니다.",
  "requestId": "req-..."
}
```

클라이언트가 분기에 사용하는 안정적인 `code`와 사용자에게 보여 주는 메시지를 구분합니다. 입력 검증 상세 정보에는 공개를 허용한 필드 경로만 포함합니다. 데이터베이스 오류, 스택, SQL은 노출하지 않습니다.

## 트랜잭션

메모 수정 유스 케이스의 순서는 다음과 같습니다.

```text
버전이 일치하는 경우에만 메모 갱신
→ 갱신되지 않으면 409
→ 활동 기록 삽입
→ 두 쓰기 모두 커밋
→ DTO 반환
```

활동 기록을 삽입하기 전에 의도적으로 예외를 발생시키는 테스트를 작성해 메모 갱신도 함께 롤백되는지 확인합니다.

## 마이그레이션

- 빈 PostgreSQL 데이터베이스에 전체 마이그레이션 적용
- 두 번째 실행 시의 처리 방식 확인
- 애플리케이션 시작과 마이그레이션 명령 분리
- 실제 스키마와 Kysely `Database` 타입 일치
- 테스트 데이터베이스마다 깨끗한 스키마 또는 고유한 데이터베이스 사용

PostgreSQL 실행 방식과 자원 정리도 프로젝트 요구사항에 포함됩니다. 기존 `05-postgresql-kysely`의 Compose 구성을 이해한 뒤 새 프로젝트에 필요한 구성을 직접 만들고, 고유한 프로젝트 이름·포트·볼륨과 종료 명령을 완료 증거에 기록합니다.

## 테스트 목록

### 단위 테스트

- 제목 정규화
- 보관된 메모 수정 거부
- 버전 증가 계산

### API 테스트

- 생성 201
- 입력 검증 실패 400
- 없는 메모 404
- 오래된 버전으로 수정 시 409
- 내부 오류 500과 상세 정보 비노출
- 안정적인 페이지네이션 정렬

### 데이터베이스 테스트

- 마이그레이션
- 제약 조건
- 메모 수정과 활동 기록의 롤백
- 같은 버전으로 동시에 갱신할 때 하나만 성공
- 연결 풀 정리

## 구현 순서

1. 요청·응답 스키마와 오류 코드를 먼저 정의합니다.
2. 메모리 리포지터리로 라우트와 서비스 흐름을 완성합니다.
3. 마이그레이션과 Kysely 타입을 작성합니다.
4. PostgreSQL 리포지터리를 연결합니다.
5. 트랜잭션과 동시성 테스트를 추가합니다.
6. 프로덕션 서버 진입점과 정상 종료를 연결합니다.
7. 깨끗한 데이터베이스에서 타입 검사와 테스트를 반복 실행합니다.

## 범위 밖

- 로그인과 쿠키
- 여러 사용자 사이의 공유
- React 화면
- WebSocket
- 고급 검색과 전문적인 인덱스 튜닝
- Docker 기반 프로덕션 배포

이 범위를 제한해야 API와 데이터베이스 경계를 독립적으로 완성할 수 있습니다.

## 완료 기준

- Fastify 애플리케이션 팩터리와 서버 진입점을 분리합니다.
- 모든 외부 입력과 응답을 런타임 스키마로 검증합니다.
- 라우트, 서비스, 리포지터리의 책임과 오류 변환 과정을 설명할 수 있습니다.
- 실제 PostgreSQL에서 마이그레이션, 제약 조건, 롤백, 경쟁 상황을 테스트합니다.
- 프로세스 종료 시 서버와 데이터베이스 연결 풀을 닫습니다.

## 완료 증거 기준

자동 정답 비교 대신 학습자 프로젝트에 다음 증거를 남깁니다. 형식은 자유지만 각 항목의 명령, 종료 코드, 관찰 결과, 실패 주입 결과를 다시 확인할 수 있어야 합니다.

| 증거 | 최소 내용 |
|---|---|
| API 계약 | 엔드포인트·상태 코드·공개 DTO·안정적인 오류 코드·범위 밖 기능 |
| 책임과 소유권 | 라우트·서비스·리포지터리·연결 풀의 책임과 종료 책임자 |
| 데이터베이스 | 빈 데이터베이스 마이그레이션, 제약 위반, 갱신+활동 기록 롤백, 두 갱신의 경쟁 결과 |
| 검증 | 타입 검사·API·DB 테스트 명령과 성공 결과, 하나 이상의 잘못된 구현 거부 결과 |
| 자원 정리 | 서버·연결 풀·Compose 프로젝트·볼륨 종료 명령과 종료 후 상태 |

`guides` 저장소에는 이 결과와 비교할 단일 모범 답안이 없습니다. 위 요구사항을 만족하는 구조는 여러 가지일 수 있으며, 자동 검증이 포함된 기본 학습 경로는 `05-postgresql-kysely`에서 끝납니다.

## 다음 단계

선택 프로젝트를 계속 확장하려면 [`공유 메모`](03-shared-notes.md)로 이동합니다. 자동 검증이 포함된 기본 경로로 돌아가려면 [`비밀번호, 세션과 쿠키`](../04-data-and-security/04-passwords-sessions-cookies.md)를 읽고 `06-security` 실습을 시작합니다.
