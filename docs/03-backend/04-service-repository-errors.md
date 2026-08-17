# 서비스·리포지터리와 오류

라우트가 입력 검증, 권한 판정, SQL, 트랜잭션, 로깅, 응답 형식을 모두 처리하면 작은 기능을 바꿔도 수정 범위가 넓어집니다. 반대로 이름만 다른 계층을 늘리면 단순 전달 함수만 쌓입니다. 각 계층은 **어떤 결정을 내리고 어떤 실패를 책임지는지**를 기준으로 나눕니다.

## 목표

- 라우트, 애플리케이션 서비스, 리포지터리의 책임을 구분합니다.
- 인터페이스와 조립 위치로 의존성을 명시합니다.
- 예상 가능한 애플리케이션 오류와 분류할 수 없는 오류를 구분합니다.
- 유스 케이스에 맞는 트랜잭션 경계를 정합니다.
- 테스트 대역과 실제 어댑터가 같은 계약을 지키게 합니다.

## 라우트의 책임

라우트는 전송 계층의 요청을 애플리케이션 호출로 변환합니다.

```ts
app.post("/boards", async (request, reply) => {
  const input = CreateBoardSchema.parse(request.body);
  const actor = requireActor(request);
  const board = await service.createBoard({ actorId: actor.id, title: input.title });
  return reply.code(201).send(toBoardDto(board));
});
```

라우트가 담당할 작업은 다음과 같습니다.

- 경로·쿼리·본문·헤더 파싱
- 인증 문맥 읽기
- 애플리케이션 명령 호출
- 결과를 응답 DTO와 상태 코드로 변환

라우트에서 직접 SQL을 실행하거나 여러 리포지터리의 작업 순서를 조정하지 않습니다.

## 애플리케이션 서비스의 책임

```ts
class BoardService {
  constructor(private boards: BoardRepository, private ids: IdGenerator, private clock: Clock) {}

  async createBoard(command: CreateBoardCommand): Promise<Board> {
    const existing = await this.boards.findByOwnerAndTitle(command.actorId, command.title);
    if (existing) throw new ConflictError("board_title_exists");
    const board = Board.create(this.ids.next(), command.actorId, command.title, this.clock.now());
    await this.boards.insert(board);
    return board;
  }
}
```

서비스는 유스 케이스의 실행 순서와 도메인 판정을 담당합니다. HTTP 상태 코드나 Fastify의 `reply` 객체를 알아서는 안 됩니다. 조회 후 삽입 사이에는 경쟁 상태가 생길 수 있으므로 고유성의 최종 보장은 데이터베이스 제약 조건에도 두고, 리포지터리 오류를 충돌 오류로 변환합니다.

## 리포지터리의 책임

리포지터리는 애플리케이션에서 필요한 저장 작업을 표현합니다.

```ts
interface BoardRepository {
  findVisibleById(actorId: string, boardId: string): Promise<Board | null>;
  insert(board: Board): Promise<void>;
  updateTitleIfVersion(input: RenameInput): Promise<Board | null>;
}
```

모든 값을 받는 일반적인 `save(any)`보다 유스 케이스와 불변식을 드러내는 작업 이름이 유용할 수 있습니다. 리포지터리는 HTTP 상태 코드를 반환하거나 라우트의 DTO를 저장하지 않습니다.

## 트랜잭션 경계

하나의 유스 케이스에서 여러 쓰기가 함께 성공하거나 함께 실패해야 한다면 서비스가 트랜잭션을 제공하는 작업 단위를 사용합니다.

```ts
await unitOfWork.transaction(async (tx) => {
  const item = await tx.items.updateIfVersion(command);
  if (!item) throw new ConflictError("stale_item");
  await tx.events.append(createEvent(item));
});
```

리포지터리 함수마다 별도 트랜잭션을 열면 항목 변경은 성공했지만 감사 이벤트 기록은 실패하는 부분 성공이 발생할 수 있습니다. 반대로 요청 전체를 불필요하게 긴 트랜잭션으로 묶고 외부 HTTP 호출까지 포함해서는 안 됩니다.

## 오류 분류

### 예상 가능한 애플리케이션 오류

- 형식 검증 이후의 도메인 규칙 위반
- 리소스 없음
- 권한 부족
- 버전 또는 고유성 충돌

이러한 오류는 안정적인 코드와 필요한 문맥을 가질 수 있습니다.

```ts
class AppError extends Error {
  constructor(readonly code: string, options?: { cause?: unknown }) {
    super(code, options);
  }
}
```

### 인프라 오류

- 데이터베이스 연결 실패
- 쿼리 타임아웃
- 디스크 또는 네트워크 오류

현재 유스 케이스에서 복구할 수 없다면 원인을 보존해 상위 경계로 전달하고 HTTP 경계에서 일반적인 서버 오류로 변환합니다. 원본 SQL 오류 메시지를 사용자에게 보내서는 안 됩니다.

## 오류 변환 경계

```text
PostgreSQL 고유성 제약 위반
→ 리포지터리 어댑터가 타입이 있는 충돌 오류로 변환
→ 서비스가 애플리케이션 오류 코드 결정
→ HTTP 오류 처리기가 409 응답 본문으로 변환
```

모든 계층에서 같은 오류를 반복해서 기록하면 중복된 스택 로그만 남습니다. 의미 있는 문맥을 추가할 수 있는 경계와 최종 요청 경계 중 어디에서 기록할지 정책을 정합니다.

## 테스트 대역

메모리 리포지터리는 빠른 서비스 테스트에 유용하지만 실제 데이터베이스와 다른 동작을 보일 수 있습니다.

다음 항목을 별도로 확인합니다.

- 고유성 제약
- 정렬과 페이지네이션
- 트랜잭션 롤백
- 동시 변경
- 대소문자와 `NULL` 처리 방식

메모리 구현은 서비스의 실행 흐름을 검사하고, 실제 PostgreSQL 통합 검사는 제약 조건과 트랜잭션 동작을 검증합니다. 어느 한쪽이 다른 쪽을 대신하지는 못합니다.

## 의존성 방향

애플리케이션 서비스는 Fastify나 Kysely의 구체 클래스보다 필요한 기능만 표현하는 작은 인터페이스에 의존합니다. 프로덕션 구성 루트에서 실제 어댑터를 연결합니다. 모든 클래스 앞에 기계적으로 인터페이스를 만들 필요는 없지만, 여러 구현·테스트 대역·소유권 경계가 실제로 존재하는 곳에는 인터페이스가 유용합니다.

## 흔한 오류

- 라우트가 SQL과 트랜잭션을 직접 관리합니다.
- 리포지터리가 HTTP 응답을 반환합니다.
- 모든 오류를 `Error("something failed")` 하나로 처리합니다.
- 인프라 오류 메시지를 클라이언트에 그대로 보냅니다.
- 트랜잭션 안에서 외부 네트워크 호출을 수행합니다.
- 메모리 리포지터리 테스트만으로 데이터베이스 제약 조건을 검증했다고 판단합니다.

## 연결 실습

[`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)에서는 메모리 리포지터리로 책임 경계를 만들고, [`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)에서는 실제 어댑터와 트랜잭션을 검증합니다.

## 완료 기준

- 라우트·서비스·리포지터리가 각각 내리는 결정을 설명합니다.
- 의존성을 조립하는 위치가 명확합니다.
- 예상 가능한 오류와 인프라 오류를 구분합니다.
- 함께 성공해야 하는 쓰기의 트랜잭션 경계를 유스 케이스에 둡니다.
- 메모리 테스트와 실제 데이터베이스 테스트가 각각 검증하는 범위를 설명합니다.

## 다음 단계

먼저 [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)의 `work/`에서 파트 03의 라우트·서비스·리포지터리·오류 계약을 검증하고, 완료한 뒤 `reference/`와 비교합니다. 그다음 저장 계층에서 보호할 관계와 불변식은 [`관계 모델과 SQL`](../04-data-and-security/01-sql-relational-model.md)에서 다룹니다.
