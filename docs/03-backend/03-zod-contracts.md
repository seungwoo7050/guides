# Zod 전송 계약

HTTP body, path parameter, query, header와 WebSocket message는 모두 신뢰할 수 없는 외부 값입니다. Zod 같은 runtime schema는 이 값을 transport DTO로 바꾸는 경계를 제공합니다. 하지만 schema가 권한, DB 상태와 모든 업무 규칙을 대신하지는 않습니다.

## 목표

- 요청의 모든 외부 위치를 runtime에서 검증합니다.
- parsing·normalization과 업무 validation을 분리합니다.
- 응답 schema로 accidental data exposure를 막습니다.
- 오류 detail을 안정된 API 형태로 바꿉니다.
- HTTP와 WebSocket에서 공유할 계약의 범위를 정합니다.

## 입력 schema

```ts
export const CreateBoardSchema = z.object({
  title: z.string().trim().min(1).max(80)
}).strict();
```

`trim` 뒤 빈 문자열이 되는 입력을 거부합니다. `.strict()`를 사용할지는 forward compatibility와 예상하지 않은 field 정책에 따라 정합니다. extra field를 조용히 제거할지 명시적으로 거부할지 API 계약입니다.

path와 query도 검사합니다.

```ts
const BoardParamsSchema = z.object({ id: z.string().uuid() });
const BoardQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  cursor: z.string().min(1).optional()
});
```

coerce는 편리하지만 빈 문자열·boolean 같은 변환 결과를 이해하고 사용합니다.

## parse와 normalize

schema는 외부 표현을 application에 적합한 값으로 정규화할 수 있습니다.

```ts
const EmailSchema = z.string().trim().toLowerCase().email();
```

그러나 사용자의 원래 표시 문자열이 필요하다면 normalization과 display value를 무조건 같은 값으로 덮지 않습니다. Unicode·locale·case sensitivity가 업무 identity에 어떤 의미인지 정합니다.

## schema validation과 업무 rule

다음은 schema가 확인할 수 있습니다.

- field 존재와 type
- 문자열 길이와 pattern
- 숫자 범위
- union message shape

다음은 service·repository 상태가 필요합니다.

- 현재 사용자가 board member인지
- title이 같은 owner 범위에서 unique인지
- baseVersion이 DB version과 같은지
- 계정이 정지되어 있는지

```text
unknown request
→ transport schema parse
→ authenticated actor
→ application command
→ service rule
→ repository transaction
```

이 순서를 섞지 않습니다.

## response schema

DB row를 바로 `reply.send`하지 않습니다.

```ts
const BoardResponseSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  role: z.enum(["owner", "editor", "viewer"]),
  version: z.number().int().nonnegative()
});
```

password hash, session digest와 internal column이 accidental하게 응답에 포함되는 것을 막습니다. framework response serialization schema를 사용할 수도 있고 mapping 뒤 test에서 parse할 수도 있습니다.

## 오류 detail

Zod issue 전체에는 internal schema path와 implementation detail이 포함될 수 있습니다. 외부 계약으로 필요한 항목만 mapping합니다.

```ts
function toValidationDetails(error: z.ZodError) {
  return error.issues.map((issue) => ({
    path: issue.path.join("."),
    reason: issue.code
  }));
}
```

사용자 메시지는 locale과 제품 wording에 따라 따로 관리할 수 있습니다. client가 Zod 내부 message에 의존하지 않게 합니다.

## 공유 package

HTTP와 WebSocket 양쪽이 같은 `BoardDto`, role과 item payload를 사용한다면 `packages/contracts`에 둘 수 있습니다. 하지만 다음은 공유하지 않습니다.

- DB client type
- repository interface 전체
- server secret configuration
- server-only error class
- UI component state

공유 package가 거대한 공통 domain이 되면 frontend와 backend 배포가 불필요하게 결합됩니다.

## WebSocket union

```ts
const ClientMessageSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.join"), boardId: z.string().uuid() }),
  z.object({ type: z.literal("item.move"), boardId: z.string().uuid(), itemId: z.string().uuid(), baseVersion: z.number().int(), x: z.number(), y: z.number(), final: z.boolean() })
]);
```

`type`으로 먼저 분기하면 message마다 필요한 field를 명확히 좁힐 수 있습니다. JSON parse 실패와 schema 실패를 connection 전체 crash로 만들지 않습니다.

## schema evolution

client와 server가 동시에 배포되지 않을 수 있습니다. optional field 추가, enum 값 추가와 field 제거의 호환성을 고려합니다. client가 알 수 없는 enum 값을 만나면 어떤 fallback을 사용할지 정합니다. 무조건 `.strict()`가 좋은지 버전 혼합 배포를 기준으로 판단합니다.

## 실패 조건

- body만 검사하고 path·query·header는 문자열로 신뢰합니다.
- assertion으로 schema parsing을 대체합니다.
- schema 통과를 권한 통과로 간주합니다.
- DB row를 response DTO로 그대로 사용합니다.
- Zod의 내부 message를 장기 public API로 고정합니다.
- server-only type을 frontend 공유 package에 넣습니다.

## 연결 실습

[`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)에서 잘못된 body·없는 자원·conflict를 서로 다른 계약으로 검사합니다.

## 완료 기준

- body·path·query와 message를 runtime parse합니다.
- normalization과 업무 validation을 구분합니다.
- response mapping으로 내부 field 노출을 막습니다.
- validation issue를 안정된 오류 detail로 변환합니다.
- 공유 계약 package의 포함·제외 범위를 설명합니다.

## 다음 단계

parse된 command를 업무 rule과 저장소에 연결하는 구조는 [`서비스·저장소와 오류`](04-service-repository-errors.md)에서 다룹니다.
