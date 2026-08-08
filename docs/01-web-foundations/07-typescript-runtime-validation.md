# TypeScript와 실행 시점 검증

TypeScript는 코드 안에서 가능한 값의 조합을 제한하지만 build 결과에서는 사라집니다. HTTP body, 환경 변수, URL, WebSocket message와 storage 값은 TypeScript compiler가 만들지 않았으므로 실행 시점에 검사해야 합니다.

## 목표

- 추론과 명시적 type annotation을 적절히 사용합니다.
- union과 narrowing으로 불가능한 상태를 줄입니다.
- `unknown`, `any`와 type assertion의 차이를 설명합니다.
- 외부 입력을 parse해 application type으로 바꿉니다.
- schema를 전송 계약으로 사용하되 domain model과 구분합니다.

## 추론과 공개 계약

지역 값은 추론에 맡기고 public function의 입력·결과는 명시하면 읽기 쉽습니다.

```ts
const retryCount = 0;

export function normalizeTitle(input: string): string {
  return input.trim();
}
```

모든 변수에 type을 반복한다고 안전성이 높아지는 것은 아닙니다. 경계와 의도를 드러내는 곳에 씁니다.

## literal union으로 가능한 값을 줄입니다

```ts
type Role = "owner" | "editor" | "viewer";
```

단순 `string`보다 허용 상태가 분명합니다. status마다 필요한 값이 다르면 판별 가능한 union을 사용합니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };
```

`ready`가 아닌데 data가 존재하거나 loading과 error가 동시에 true인 상태를 type 수준에서 만들기 어렵게 합니다.

## narrowing과 exhaustive 처리

```ts
function renderState(state: LoadState<string[]>) {
  switch (state.status) {
    case "idle": return "시작 전";
    case "loading": return "불러오는 중";
    case "ready": return `${state.data.length}개`;
    case "error": return state.message;
    default: return assertNever(state);
  }
}

function assertNever(value: never): never {
  throw new Error(`처리하지 않은 상태: ${JSON.stringify(value)}`);
}
```

새 상태를 추가했을 때 누락된 분기가 compile error로 드러납니다.

## `unknown`은 검사 전 값을 표현합니다

```ts
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
```

`unknown`에서는 속성을 바로 읽을 수 없으므로 조건으로 좁혀야 합니다. `any`는 대부분의 검사를 끄므로 외부 입력 문제를 뒤로 미룹니다.

## assertion은 검증이 아닙니다

```ts
const board = JSON.parse(text) as Board;
```

이 코드는 runtime 값을 바꾸거나 누락 field를 거부하지 않습니다. compiler에게 “내가 확신한다”고 말할 뿐입니다.

직접 parser를 쓸 수 있습니다.

```ts
function parseBoard(value: unknown): Board {
  if (!isRecord(value)) throw new Error("board는 객체여야 합니다.");
  if (typeof value.id !== "string" || !value.id) throw new Error("id가 필요합니다.");
  if (typeof value.title !== "string" || !value.title.trim()) throw new Error("title이 필요합니다.");
  return { id: value.id, title: value.title.trim() };
}
```

## schema library

Zod 같은 library는 선언과 parsing을 함께 제공합니다.

```ts
const BoardSchema = z.object({
  id: z.string().uuid(),
  title: z.string().trim().min(1).max(80),
  version: z.number().int().nonnegative()
});

type BoardDto = z.infer<typeof BoardSchema>;
const board = BoardSchema.parse(await response.json());
```

schema가 compile-time type과 runtime parser를 연결하지만 모든 domain rule을 자동으로 표현하지는 않습니다. 예를 들어 “현재 사용자가 owner여야 함”, “DB의 현재 version과 같아야 함”은 context와 저장소 상태가 필요한 업무 검증입니다.

## 전송 DTO와 domain type

HTTP JSON에는 Date object, class method와 database connection을 보낼 수 없습니다. 전송 type은 직렬화 가능한 값과 공개 field만 가집니다.

```ts
type BoardDto = {
  id: string;
  title: string;
  updatedAt: string;
};
```

DB row를 그대로 응답 type으로 사용하면 내부 열 추가·이름 변경과 개인정보 노출이 API 호환성 문제가 됩니다. route boundary에서 mapping합니다.

## 환경 변수도 외부 입력입니다

```ts
const EnvSchema = z.object({
  PORT: z.coerce.number().int().min(1).max(65535),
  DATABASE_URL: z.string().url(),
  NODE_ENV: z.enum(["development", "test", "production"])
});

export const env = EnvSchema.parse(process.env);
```

사용 시점마다 기본값을 흩뿌리지 않고 startup에서 한 번 검증해 잘못된 process가 요청을 받기 전에 실패하게 합니다.

## type boundary의 방향

권장 흐름은 다음입니다.

```text
unknown 외부 값
→ runtime schema parse
→ transport DTO
→ application command
→ domain·service rule
→ repository
```

반환도 반대 방향으로 mapping합니다. schema를 database model 전체에 무분별하게 공유하지 않습니다.

## 실패 조건

- `any`와 assertion으로 외부 입력을 신뢰합니다.
- 여러 boolean으로 모순 상태를 만듭니다.
- schema 통과를 권한·업무 규칙 통과로 착각합니다.
- DB row type을 public API로 그대로 내보냅니다.
- 환경 변수를 사용하는 곳마다 제각각 변환합니다.

## 연결 실습

[`실행 환경과 작업 공간`](../../exercises/01-runtime/README.md)은 `unknown` 포트를, [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)는 실제 HTTP body와 오류 응답을 검증합니다.

## 완료 기준

- `unknown`, `any`, assertion의 차이를 설명할 수 있습니다.
- union으로 화면 상태와 role을 제한합니다.
- 외부 JSON과 환경 변수를 runtime에서 parse합니다.
- schema 검증과 context-dependent 업무 검증을 구분합니다.
- transport·application·database type의 경계를 설명합니다.

## 다음 단계

TypeScript 코드가 실제로 설치·실행·공유되는 경계는 [`Node.js, package와 workspace`](08-node-packages-workspaces.md)에서 다룹니다.
