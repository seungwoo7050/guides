# Fastify 생명주기

Fastify route를 몇 개 등록하는 것만으로 유지 가능한 server가 되지는 않습니다. application factory, plugin scope, hook, dependency 조립, 실제 port listen과 close를 분리해야 test·startup validation·graceful shutdown이 같은 계약을 공유합니다.

## 목표

- app factory와 실행 entry를 분리합니다.
- plugin의 encapsulation과 등록 순서를 이해합니다.
- hook을 요청 수명에 맞게 사용합니다.
- dependency를 명시적으로 조립합니다.
- startup·readiness·shutdown을 검증합니다.

## app factory

```ts
export async function buildApp(deps: Dependencies) {
  const app = Fastify({ logger: deps.logger });
  await app.register(errorPlugin);
  await app.register(boardRoutes, { service: deps.boardService });
  return app;
}
```

factory는 port를 열지 않습니다. test는 독립 dependency로 app을 만들고 `app.inject`를 사용합니다.

```ts
const app = await buildApp(createTestDependencies());
const response = await app.inject({ method: "GET", url: "/boards" });
await app.close();
```

실제 entry만 listen합니다.

```ts
const deps = await createProductionDependencies(env);
const app = await buildApp(deps);
await app.listen({ host: "0.0.0.0", port: env.PORT });
```

## plugin과 scope

Fastify plugin은 route 묶음뿐 아니라 decorator, hook와 prefix의 캡슐화 경계입니다. 등록 순서와 scope 밖에서는 decorator가 보이지 않을 수 있습니다.

```ts
await app.register(async function boardPlugin(scope) {
  scope.decorateRequest("actor", null);
  scope.addHook("preHandler", authenticate);
  await scope.register(boardRoutes, { prefix: "/boards" });
});
```

모든 route에 전역 hook을 붙이면 공개 health endpoint와 인증 route까지 불필요하게 막힐 수 있습니다. 필요한 scope에 둡니다.

## hook 수명

요청 흐름의 대표 위치:

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

- request id·기본 context: early hook
- authentication: body가 필요 없다면 `onRequest` 또는 `preHandler`
- schema validation: Fastify validation 경계
- authorization: route context와 parsed parameter가 필요한 `preHandler`
- metric·cleanup: `onResponse` 또는 error path까지 포함하는 hook

hook에서 reply를 보냈으면 이후 handler가 실행되지 않게 명확히 return합니다.

## dependency injection

```ts
type Dependencies = {
  boardService: BoardService;
  sessionService: SessionService;
  clock: Clock;
  ids: IdGenerator;
};
```

module 전역 singleton 대신 app 생성 시 dependency를 전달합니다. test마다 독립 repository, clock과 id generator를 사용하면 순서 의존과 실제 timer를 줄일 수 있습니다.

Fastify decorator를 사용할 수도 있지만 타입 확장과 plugin scope를 관리합니다. 핵심은 숨은 import singleton이 아니라 조립 위치가 한눈에 보이는 것입니다.

## 환경과 startup

```ts
const env = EnvSchema.parse(process.env);
```

port, database URL, cookie 설정과 허용 origin을 startup에서 검증합니다. migration을 server startup에 자동 실행할지 별도 release 단계로 둘지 명시합니다. 운영에서는 여러 instance가 동시에 migration을 시도하는 문제를 고려합니다.

## liveness와 readiness

- liveness: process event loop가 살아 있고 복구 불가능한 deadlock이 아닌가
- readiness: 지금 새 요청을 받아도 되는가

DB가 잠시 느리다고 process를 즉시 재시작하는 liveness는 재시작 폭풍을 만들 수 있습니다. readiness는 새 traffic을 막고 dependency 회복을 기다리는 선택을 할 수 있습니다. endpoint가 secret과 내부 topology를 과도하게 노출하지 않게 합니다.

## error handler

예상 가능한 application error를 HTTP 오류로 번역하고, 알 수 없는 오류는 request id와 원인을 log한 뒤 일반 500을 반환합니다.

```ts
app.setErrorHandler((error, request, reply) => {
  if (error instanceof NotFoundError) {
    return reply.code(404).send(toErrorBody(error, request.id));
  }
  request.log.error({ err: error }, "unhandled request error");
  return reply.code(500).send({ code: "internal_error", message: "요청을 처리하지 못했습니다.", requestId: request.id });
});
```

validation error의 detail 공개 범위도 여기서 안정화할 수 있습니다.

## shutdown

`app.close()`는 Fastify server와 plugin close hook을 실행합니다. DB pool, WebSocket heartbeat, queue consumer는 plugin `onClose`나 production dependency container의 close 계약에 연결합니다.

```ts
app.addHook("onClose", async () => {
  await db.destroy();
});
```

중복 signal에서 close를 여러 번 경쟁시키지 않고, 최대 종료 시간과 강제 종료 정책을 정합니다.

## 실패 조건

- module import가 즉시 port를 엽니다.
- test가 실제 port와 전역 singleton을 공유합니다.
- 인증 hook을 모든 route에 무조건 등록합니다.
- hook에서 reply 후 handler 실행을 명확히 멈추지 않습니다.
- startup validation 없이 첫 요청에서 환경 오류가 발생합니다.
- app.close 뒤 pool·timer·consumer가 남습니다.

## 연결 실습

[`Fastify와 Zod API`](../../exercises/04-fastify-zod-api/README.md)는 app factory와 `app.inject`를 사용해 route·hook·serialization을 검사합니다.

## 완료 기준

- app factory와 listen entry를 분리합니다.
- plugin scope와 hook 위치를 선택한 이유를 설명합니다.
- dependency를 app 생성 시 조립합니다.
- startup validation과 readiness를 구분합니다.
- close 뒤 server와 모든 owned resource가 종료됩니다.

## 다음 단계

요청·응답을 실제 application 값으로 바꾸는 경계는 [`Zod 전송 계약`](03-zod-contracts.md)에서 다룹니다.
