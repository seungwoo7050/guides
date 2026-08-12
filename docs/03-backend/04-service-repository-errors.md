# 서비스·저장소와 오류

route가 validation, 권한, SQL, transaction, log와 응답 formatting을 모두 처리하면 작은 기능도 수정 범위가 넓어집니다. 반대로 계층을 이름만 늘리면 단순 전달 함수가 쌓입니다. 책임을 **어떤 결정을 내리고 어떤 실패를 소유하는가**로 나눕니다.

## 목표

- route, application service와 repository의 책임을 구분합니다.
- dependency를 interface와 조립 위치로 명시합니다.
- 예상 가능한 application error와 알 수 없는 오류를 구분합니다.
- transaction boundary를 use case에 맞게 둡니다.
- test double과 실제 adapter의 계약을 동일하게 유지합니다.

## route 책임

route는 transport를 application 호출로 바꿉니다.

```ts
app.post("/boards", async (request, reply) => {
  const input = CreateBoardSchema.parse(request.body);
  const actor = requireActor(request);
  const board = await service.createBoard({ actorId: actor.id, title: input.title });
  return reply.code(201).send(toBoardDto(board));
});
```

route가 담당할 것:

- path·query·body·header parse
- authentication context 읽기
- application command 호출
- result를 response DTO와 status로 변환

route가 직접 SQL과 여러 repository를 조정하지 않습니다.

## application service 책임

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

service는 use case 순서와 업무 판정을 소유합니다. HTTP status나 Fastify reply를 알지 않습니다. 실제 uniqueness의 최종 보장은 DB constraint에도 있어야 하며 repository 오류를 conflict로 번역할 수 있습니다.

## repository 책임

repository는 application이 필요로 하는 저장 작업을 표현합니다.

```ts
interface BoardRepository {
  findVisibleById(actorId: string, boardId: string): Promise<Board | null>;
  insert(board: Board): Promise<void>;
  updateTitleIfVersion(input: RenameInput): Promise<Board | null>;
}
```

일반적인 `save(any)`보다 use case와 불변식이 드러나는 operation이 유용할 수 있습니다. repository가 HTTP status를 반환하거나 route DTO를 저장하지 않습니다.

## transaction boundary

하나의 use case에서 여러 쓰기가 함께 성공해야 하면 service가 transaction-capable unit을 요청합니다.

```ts
await unitOfWork.transaction(async (tx) => {
  const item = await tx.items.updateIfVersion(command);
  if (!item) throw new ConflictError("stale_item");
  await tx.events.append(createEvent(item));
});
```

repository 함수마다 독립 transaction을 열면 item update는 성공하고 audit event는 실패할 수 있습니다. 반대로 request 전체를 불필요하게 긴 transaction으로 잡아 external HTTP 호출까지 포함하지 않습니다.

## 오류 분류

### 예상 가능한 application error

- validation 이후의 업무 거부
- 자원 없음
- 권한 부족
- version·uniqueness conflict

stable code와 필요한 context를 가질 수 있습니다.

```ts
class AppError extends Error {
  constructor(readonly code: string, options?: { cause?: unknown }) {
    super(code, options);
  }
}
```

### infrastructure error

- DB 연결 실패
- query timeout
- disk·network 오류

현재 use case가 복구할 수 없다면 cause를 보존해 위로 전달하고 HTTP boundary에서 일반 오류로 바꿉니다. raw SQL message를 user error로 보내지 않습니다.

## 오류 번역 경계

```text
PostgreSQL unique violation
→ repository adapter가 typed conflict로 번역
→ service가 application code 결정
→ HTTP error handler가 409 body로 번역
```

모든 layer에서 같은 오류를 log하면 중복 stack이 생깁니다. 충분한 context를 추가할 수 있는 boundary와 최종 요청 경계에서 기록하는 정책을 정합니다.

## test double

메모리 repository는 빠른 service test에 유용하지만 실제 DB와 다른 계약을 만들 수 있습니다.

확인할 항목:

- uniqueness
- sorting과 pagination
- transaction rollback
- concurrent update
- case·null semantics

메모리 구현은 service flow를 검사하고, 실제 PostgreSQL 통합 검사는 제약·transaction을 증명합니다. 하나가 다른 것을 대체하지 않습니다.

## dependency direction

application service는 Fastify·Kysely 구체 class보다 작은 interface에 의존합니다. production composition root가 실제 adapter를 연결합니다. interface를 모든 class 앞에 기계적으로 만들 필요는 없지만, 다른 구현·test double·소유권 경계가 실제로 있는 곳에 둡니다.

## 실패 조건

- route가 SQL과 transaction을 직접 소유합니다.
- repository가 HTTP response를 반환합니다.
- 모든 오류를 `Error("something failed")`로 뭉갭니다.
- infrastructure message를 그대로 client에 보냅니다.
- transaction이 external network 호출까지 잡고 있습니다.
- 메모리 repository 테스트만으로 DB 제약을 증명합니다.

## 연결 실습

[`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)는 메모리 repository로 책임 경계를 만들고, [`PostgreSQL과 Kysely`](../../exercises/05-postgresql-kysely/README.md)는 실제 adapter와 transaction을 검증합니다.

## 완료 기준

- route·service·repository가 내리는 결정을 설명합니다.
- dependency 조립 위치가 명확합니다.
- 예상 가능한 오류와 infrastructure 오류를 구분합니다.
- 함께 성공할 쓰기의 transaction boundary를 use case에 둡니다.
- 메모리·실제 DB 검사가 각각 증명하는 범위를 설명합니다.

## 다음 단계

먼저 [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)의 생성된 `work/`에서 Part 03의 route·service·repository·error 계약을 검증하고 완료 뒤 `reference/`와 비교합니다. 그다음 저장소가 보호할 관계와 불변식은 [`관계 모델과 SQL`](../04-data-and-security/01-sql-relational-model.md)에서 다룹니다.
