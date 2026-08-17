# Zod 전송 계약

HTTP 본문, 경로 매개변수, 쿼리, 헤더, WebSocket 메시지는 모두 신뢰할 수 없는 외부 값입니다. Zod 같은 런타임 스키마는 이러한 값을 검증된 전송 DTO로 변환하는 경계를 제공합니다. 다만 스키마가 권한, 데이터베이스 상태, 모든 도메인 규칙을 대신할 수는 없습니다.

## 목표

- 요청의 모든 외부 입력을 런타임에 검증합니다.
- 파싱·정규화와 도메인 검증을 분리합니다.
- 응답 스키마로 의도하지 않은 데이터 노출을 막습니다.
- 검증 오류 세부 정보를 일관된 API 형식으로 변환합니다.
- HTTP와 WebSocket에서 공유할 계약의 범위를 정합니다.

## 입력 스키마

```ts
export const CreateBoardSchema = z.object({
  title: z.string().trim().min(1).max(80)
}).strict();
```

`trim`한 뒤 빈 문자열이 되는 입력을 거부합니다. `.strict()` 사용 여부는 향후 호환성과 알 수 없는 필드의 처리 정책에 따라 정합니다. 추가 필드를 조용히 제거할지 명시적으로 거부할지는 API 계약의 일부입니다.

경로 매개변수와 쿼리도 검증합니다.

```ts
const BoardParamsSchema = z.object({ id: z.string().uuid() });
const BoardQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  cursor: z.string().min(1).optional()
});
```

강제 변환은 편리하지만 빈 문자열이나 불리언 같은 값이 어떤 결과로 변환되는지 이해하고 사용해야 합니다.

## 파싱과 정규화

스키마는 외부 표현을 애플리케이션에서 사용할 형태로 정규화할 수 있습니다.

```ts
const EmailSchema = z.string().trim().toLowerCase().email();
```

사용자가 입력한 원래 표시 문자열이 필요하다면 정규화한 값으로 무조건 덮어쓰지 않습니다. 유니코드, 로케일, 대소문자 구분이 도메인의 식별 규칙에서 어떤 의미를 가지는지 먼저 정해야 합니다.

## 스키마 검증과 도메인 규칙

스키마가 확인할 수 있는 항목은 다음과 같습니다.

- 필드 존재 여부와 타입
- 문자열 길이와 패턴
- 숫자 범위
- 유니온 메시지 구조

다음 항목은 서비스나 리포지터리의 현재 상태가 필요합니다.

- 현재 사용자가 보드 구성원인지
- 같은 소유자 범위에서 제목이 고유한지
- `baseVersion`이 데이터베이스의 현재 버전과 같은지
- 계정이 정지 상태인지

```text
검증되지 않은 요청
→ 전송 스키마 파싱
→ 인증된 사용자 문맥
→ 애플리케이션 명령
→ 서비스의 도메인 규칙
→ 리포지터리 트랜잭션
```

각 경계의 책임을 섞지 않습니다.

## 응답 스키마

데이터베이스 행을 그대로 `reply.send`에 전달하지 않습니다.

```ts
const BoardResponseSchema = z.object({
  id: z.string().uuid(),
  title: z.string(),
  role: z.enum(["owner", "editor", "viewer"]),
  version: z.number().int().nonnegative()
});
```

비밀번호 해시, 세션 다이제스트, 내부 열이 실수로 응답에 포함되는 것을 막습니다. 프레임워크의 응답 직렬화 스키마를 사용하거나, DTO로 변환한 뒤 테스트에서 스키마를 다시 적용할 수 있습니다.

## 오류 세부 정보

Zod의 issue 전체에는 내부 스키마 경로와 구현 세부 정보가 포함될 수 있습니다. 외부 계약에 필요한 항목만 골라 변환합니다.

```ts
function toValidationDetails(error: z.ZodError) {
  return error.issues.map((issue) => ({
    path: issue.path.join("."),
    reason: issue.code
  }));
}
```

사용자 메시지는 제품 문구와 로케일에 맞춰 별도로 관리할 수 있습니다. 클라이언트가 Zod 내부 메시지에 직접 의존하지 않게 합니다.

## 공유 패키지

HTTP와 WebSocket이 같은 `BoardDto`, 역할, 항목 페이로드를 사용한다면 `packages/contracts`에 공유할 수 있습니다. 다음 항목은 공유하지 않습니다.

- 데이터베이스 클라이언트 타입
- 리포지터리 인터페이스 전체
- 서버 비밀 설정
- 서버 전용 오류 클래스
- UI 컴포넌트 상태

공유 패키지에 서버 도메인 전체를 넣으면 프런트엔드와 백엔드의 배포가 불필요하게 결합됩니다.

## WebSocket 유니온

```ts
const ClientMessageSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("board.join"), boardId: z.string().uuid() }),
  z.object({ type: z.literal("item.move"), boardId: z.string().uuid(), itemId: z.string().uuid(), baseVersion: z.number().int(), x: z.number(), y: z.number(), final: z.boolean() })
]);
```

`type` 필드로 먼저 분기하면 메시지 유형마다 필요한 필드를 명확하게 좁힐 수 있습니다. JSON 파싱 실패나 스키마 검증 실패 때문에 서버 프로세스나 연결 처리 전체가 비정상 종료되지 않게 합니다.

## 스키마 변경과 호환성

클라이언트와 서버가 동시에 배포되지 않을 수 있습니다. 선택 필드 추가, 열거형 값 추가, 필드 제거가 이전 버전과 호환되는지 검토합니다. 클라이언트가 알 수 없는 열거형 값을 받았을 때의 대체 동작도 정해야 합니다. `.strict()`가 항상 최선이라고 가정하지 말고 여러 버전이 함께 동작하는 배포 상황을 기준으로 판단합니다.

## 흔한 오류

- 요청 본문만 검사하고 경로·쿼리·헤더는 문자열로 신뢰합니다.
- 타입 단언으로 스키마 파싱을 대신합니다.
- 스키마를 통과하면 권한 검사도 통과한 것으로 간주합니다.
- 데이터베이스 행을 응답 DTO로 그대로 사용합니다.
- Zod의 내부 메시지를 장기간 유지해야 하는 공개 API로 사용합니다.
- 서버 전용 타입을 프런트엔드 공유 패키지에 넣습니다.

## 연결 실습

[`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)에서 잘못된 본문, 존재하지 않는 리소스, 상태 충돌을 서로 다른 계약으로 검사합니다.

## 완료 기준

- 본문·경로·쿼리·메시지를 런타임에 파싱합니다.
- 정규화와 도메인 검증을 구분합니다.
- 응답 변환으로 내부 필드 노출을 막습니다.
- 검증 issue를 일관된 오류 세부 정보로 변환합니다.
- 공유 계약 패키지에 포함할 항목과 제외할 항목을 설명합니다.

## 다음 단계

파싱한 명령을 도메인 규칙과 저장소에 연결하는 구조는 [`서비스·리포지터리와 오류`](04-service-repository-errors.md)에서 다룹니다.
