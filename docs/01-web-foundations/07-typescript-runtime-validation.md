# TypeScript와 런타임 검증

TypeScript는 코드 안에서 허용할 값의 범위를 제한하지만 빌드 결과에서는 타입 정보가 사라집니다. HTTP 본문, 환경 변수, URL, WebSocket 메시지, 브라우저 저장소 값은 TypeScript 컴파일러가 생성한 값이 아니므로 런타임에 검증해야 합니다.

## 목표

- 타입 추론과 명시적 타입 표기를 적절히 사용합니다.
- 유니온 타입과 타입 좁히기로 불가능한 상태를 줄입니다.
- `unknown`, `any`, 타입 단언의 차이를 설명합니다.
- 외부 입력을 파싱해 애플리케이션 타입으로 변환합니다.
- 스키마를 전송 계약으로 사용하되 도메인 모델과 구분합니다.

## 타입 추론과 공개 계약

지역 변수는 타입 추론에 맡기고, 외부에 공개하는 함수의 매개변수와 반환 타입은 명시하면 코드를 이해하기 쉽습니다.

```ts
const retryCount = 0;

export function normalizeTitle(input: string): string {
  return input.trim();
}
```

모든 변수에 타입을 반복해서 표기한다고 안전성이 높아지는 것은 아닙니다. 타입 표기는 경계와 의도를 명확하게 드러내야 하는 곳에 사용합니다.

## 리터럴 유니온으로 가능한 값을 제한합니다

```ts
type Role = "owner" | "editor" | "viewer";
```

단순한 `string`보다 허용되는 값이 명확합니다. 상태마다 필요한 데이터가 다르면 판별 가능한 유니온을 사용합니다.

```ts
type LoadState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; message: string };
```

이 구조는 `ready` 상태가 아닌데 `data`가 있거나, 대기 상태와 오류 상태가 동시에 설정되는 모순을 타입 수준에서 만들기 어렵게 합니다.

## 타입 좁히기와 빠짐없는 분기 처리

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

새 상태를 추가하고 분기 처리를 빠뜨리면 컴파일 오류로 확인할 수 있습니다.

## `unknown`은 검증 전의 값을 나타냅니다

```ts
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
```

`unknown` 값의 속성은 바로 읽을 수 없으므로 조건문으로 타입을 좁혀야 합니다. `any`는 대부분의 타입 검사를 비활성화하므로 외부 입력의 문제를 런타임으로 미룰 뿐입니다.

## 타입 단언은 검증이 아닙니다

```ts
const board = JSON.parse(text) as Board;
```

이 코드는 런타임 값을 변환하지 않으며 누락된 필드도 거부하지 않습니다. 컴파일러에게 해당 값의 타입을 개발자가 보장한다고 알릴 뿐입니다.

직접 파서를 작성할 수 있습니다.

```ts
function parseBoard(value: unknown): Board {
  if (!isRecord(value)) throw new Error("board는 객체여야 합니다.");
  if (typeof value.id !== "string" || !value.id) throw new Error("id가 필요합니다.");
  if (typeof value.title !== "string" || !value.title.trim()) throw new Error("title이 필요합니다.");
  return { id: value.id, title: value.title.trim() };
}
```

## 스키마 라이브러리

Zod 같은 라이브러리는 데이터 구조 선언과 런타임 파싱 기능을 함께 제공합니다.

```ts
const BoardSchema = z.object({
  id: z.string().uuid(),
  title: z.string().trim().min(1).max(80),
  version: z.number().int().nonnegative()
});

type BoardDto = z.infer<typeof BoardSchema>;
const board = BoardSchema.parse(await response.json());
```

스키마는 컴파일 시점 타입과 런타임 파서를 연결하지만 모든 도메인 규칙을 자동으로 표현하지는 못합니다. 예를 들어 “현재 사용자가 소유자여야 한다”거나 “데이터베이스의 현재 버전과 일치해야 한다”는 규칙은 요청 문맥과 저장된 상태를 함께 확인해야 합니다.

## 전송 DTO와 도메인 타입

HTTP JSON에는 `Date` 객체, 클래스 메서드, 데이터베이스 연결 객체를 전송할 수 없습니다. 전송 타입은 직렬화 가능한 값과 외부에 공개할 필드만 포함해야 합니다.

```ts
type BoardDto = {
  id: string;
  title: string;
  updatedAt: string;
};
```

데이터베이스 행 타입을 응답 타입으로 그대로 사용하면 내부 열의 추가·이름 변경이나 개인정보 노출이 API 호환성 문제로 이어질 수 있습니다. 라우트 경계에서 명시적으로 변환합니다.

## 환경 변수도 외부 입력입니다

```ts
const EnvSchema = z.object({
  PORT: z.coerce.number().int().min(1).max(65535),
  DATABASE_URL: z.string().url(),
  NODE_ENV: z.enum(["development", "test", "production"])
});

export const env = EnvSchema.parse(process.env);
```

환경 변수를 사용하는 곳마다 기본값과 변환 로직을 흩어 놓지 않습니다. 프로세스 시작 시 한 번 검증하고, 설정이 잘못된 프로세스가 요청을 받기 전에 종료되게 합니다.

## 타입 경계의 방향

권장 흐름은 다음과 같습니다.

```text
외부에서 들어온 unknown 값
→ 런타임 스키마 파싱
→ 전송 DTO
→ 애플리케이션 명령
→ 도메인·서비스 규칙
→ 리포지터리
```

응답은 반대 방향으로 변환합니다. 하나의 스키마를 데이터베이스 모델 전체에 무분별하게 공유해서는 안 됩니다.

## 흔한 오류

- `any`와 타입 단언으로 외부 입력을 검증 없이 신뢰합니다.
- 여러 불리언 값으로 모순된 상태를 만듭니다.
- 스키마를 통과하면 권한과 도메인 규칙도 통과한 것으로 간주합니다.
- 데이터베이스 행 타입을 공개 API 응답에 그대로 사용합니다.
- 환경 변수를 사용하는 위치마다 제각각 변환합니다.

## 연결 실습

[`실행 환경과 워크스페이스`](../../exercises/01-runtime/README.md)에서는 `unknown` 타입의 포트 값을, [`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)에서는 실제 HTTP 본문과 오류 응답을 검증합니다.

## 완료 기준

- `unknown`, `any`, 타입 단언의 차이를 설명할 수 있습니다.
- 유니온 타입으로 화면 상태와 역할을 제한합니다.
- 외부 JSON과 환경 변수를 런타임에 파싱합니다.
- 스키마 검증과 요청 문맥에 의존하는 도메인 검증을 구분합니다.
- 전송·애플리케이션·데이터베이스 타입의 경계를 설명합니다.

## 다음 단계

TypeScript 코드가 설치·실행·공유되는 경계는 [`Node.js, 패키지와 워크스페이스`](08-node-packages-workspaces.md)에서 다룹니다.
