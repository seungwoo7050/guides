# Fastify 생명주기

Fastify 라우트를 몇 개 등록하는 것만으로 유지보수 가능한 서버가 되지는 않습니다. 애플리케이션 팩터리, 플러그인 범위, 훅, 의존성 조립, 실제 포트 바인딩, 종료 처리를 분리해야 테스트·시작 시점 검증·정상 종료가 같은 계약을 공유할 수 있습니다.

## 목표

- 애플리케이션 팩터리와 실행 진입점을 분리합니다.
- 플러그인의 캡슐화와 등록 순서를 이해합니다.
- 훅을 요청 생명주기에 맞게 사용합니다.
- 의존성을 명시적으로 조립합니다.
- 시작·준비 상태·종료 과정을 검증합니다.

## 애플리케이션 팩터리

```ts
export async function buildApp(deps: Dependencies) {
  const app = Fastify({ logger: deps.logger });
  await app.register(errorPlugin);
  await app.register(boardRoutes, { service: deps.boardService });
  return app;
}
```

팩터리는 포트를 열지 않습니다. 테스트에서는 독립적인 의존성으로 애플리케이션을 만들고 `app.inject`를 사용합니다.

```ts
const app = await buildApp(createTestDependencies());
const response = await app.inject({ method: "GET", url: "/boards" });
await app.close();
```

실제 실행 진입점에서만 `listen`을 호출합니다.

```ts
const deps = await createProductionDependencies(env);
const app = await buildApp(deps);
await app.listen({ host: "0.0.0.0", port: env.PORT });
```

## 플러그인과 캡슐화 범위

Fastify 플러그인은 라우트 묶음뿐 아니라 데코레이터, 훅, 경로 접두사를 캡슐화하는 경계입니다. 등록 순서와 플러그인 범위에 따라 데코레이터가 보이지 않을 수 있습니다.

```ts
await app.register(async function boardPlugin(scope) {
  scope.decorateRequest("actor", null);
  scope.addHook("preHandler", authenticate);
  await scope.register(boardRoutes, { prefix: "/boards" });
});
```

모든 라우트에 전역 인증 훅을 붙이면 공개 상태 확인 엔드포인트와 로그인 라우트까지 불필요하게 차단할 수 있습니다. 훅은 필요한 플러그인 범위에 등록합니다.

## 훅 생명주기

대표적인 요청 처리 순서는 다음과 같습니다.

```text
onRequest
→ preParsing
→ preValidation
→ preHandler
→ handler
→ preSerialization
→ onSend
→ onResponse
```

- 요청 ID와 기본 요청 문맥 생성: 초기 훅
- 인증: 요청 본문이 필요 없다면 `onRequest` 또는 `preHandler`
- 스키마 검증: Fastify의 검증 경계
- 권한 검사: 라우트 문맥과 파싱된 매개변수가 필요한 `preHandler`
- 메트릭과 자원 정리: 오류 경로까지 고려한 훅과 `onResponse`

훅에서 응답을 보냈다면 이후 처리기가 실행되지 않도록 명시적으로 반환합니다.

## 의존성 주입

```ts
type Dependencies = {
  boardService: BoardService;
  sessionService: SessionService;
  clock: Clock;
  ids: IdGenerator;
};
```

모듈 전역 싱글턴 대신 애플리케이션을 만들 때 의존성을 전달합니다. 테스트마다 독립적인 리포지터리, 시계, ID 생성기를 사용하면 테스트 실행 순서 의존성과 실제 타이머 사용을 줄일 수 있습니다.

Fastify 데코레이터를 사용할 수도 있지만 타입 확장과 플러그인 범위를 함께 관리해야 합니다. 핵심은 숨은 싱글턴 가져오기 대신 의존성 조립 위치를 한눈에 확인할 수 있게 하는 것입니다.

## 환경 검증과 시작 과정

```ts
const env = EnvSchema.parse(process.env);
```

포트, 데이터베이스 URL, 쿠키 설정, 허용할 출처를 프로세스 시작 시 검증합니다. 마이그레이션을 서버 시작 과정에서 자동으로 실행할지 별도의 배포 단계에서 실행할지도 정해야 합니다. 운영 환경에서는 여러 인스턴스가 동시에 같은 마이그레이션을 시도할 가능성을 고려합니다.

## liveness와 readiness

- liveness: 프로세스를 재시작해야 할 정도로 복구 불가능한 상태인가
- readiness: 현재 새 요청을 받아 처리할 준비가 되었는가

데이터베이스가 잠시 느리다는 이유로 liveness 검사가 실패해 프로세스를 계속 재시작하면 재시작 폭풍이 발생할 수 있습니다. readiness를 실패시켜 새 트래픽만 차단하고 의존성이 회복되기를 기다리는 방식을 선택할 수 있습니다. 상태 확인 엔드포인트에 비밀값이나 내부 네트워크 구조를 과도하게 노출해서는 안 됩니다.

## 오류 처리기

예상 가능한 애플리케이션 오류는 적절한 HTTP 오류로 변환합니다. 분류할 수 없는 오류는 요청 ID와 원인을 로그에 남기고 일반적인 500 응답을 반환합니다.

```ts
app.setErrorHandler((error, request, reply) => {
  if (error instanceof NotFoundError) {
    return reply.code(404).send(toErrorBody(error, request.id));
  }
  request.log.error({ err: error }, "unhandled request error");
  return reply.code(500).send({ code: "internal_error", message: "요청을 처리하지 못했습니다.", requestId: request.id });
});
```

검증 오류의 세부 정보를 어느 범위까지 외부에 공개할지도 이 경계에서 일관되게 변환할 수 있습니다.

## 종료 처리

`app.close()`는 Fastify 서버를 닫고 플러그인의 종료 훅을 실행합니다. 데이터베이스 풀, WebSocket 하트비트, 큐 소비자는 플러그인의 `onClose` 훅이나 프로덕션 의존성 컨테이너의 종료 계약에 연결합니다.

```ts
app.addHook("onClose", async () => {
  await db.destroy();
});
```

중복 시그널이 들어왔을 때 여러 종료 작업이 경쟁하지 않게 하고, 최대 종료 시간과 강제 종료 정책을 정합니다.

## 흔한 오류

- 모듈을 가져오는 즉시 포트를 엽니다.
- 테스트가 실제 포트와 전역 싱글턴을 공유합니다.
- 인증 훅을 모든 라우트에 무조건 등록합니다.
- 훅에서 응답한 뒤 후속 처리기의 실행을 명확히 중단하지 않습니다.
- 시작 시점에 환경을 검증하지 않아 첫 요청에서 설정 오류가 발생합니다.
- `app.close()` 뒤에도 데이터베이스 풀·타이머·소비자가 남습니다.

## 연결 실습

[`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)에서는 애플리케이션 팩터리와 `app.inject`를 사용해 라우트·훅·직렬화를 검사합니다.

## 완료 기준

- 애플리케이션 팩터리와 `listen` 진입점을 분리합니다.
- 플러그인 범위와 훅 위치를 선택한 이유를 설명합니다.
- 애플리케이션 생성 시 의존성을 조립합니다.
- 시작 시점 검증과 readiness 검사를 구분합니다.
- 종료 후 서버와 서버가 소유한 모든 자원이 정리됩니다.

## 다음 단계

요청과 응답을 애플리케이션이 사용하는 값으로 변환하는 경계는 [`Zod 전송 계약`](03-zod-contracts.md)에서 다룹니다.
