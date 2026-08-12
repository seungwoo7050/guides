# Fastify와 Zod API

외부 요청을 `unknown`으로 취급하고 실행 시점에 검증합니다. route, service, repository의 책임을 나누고 400·404·409와 내부 오류를 안정적으로 구분합니다.

## 선행 문서

- [`HTTP API 모델`](../../docs/03-backend/01-http-api-model.md)
- [`Fastify 생명주기`](../../docs/03-backend/02-fastify-lifecycle.md)
- [`Zod 전송 계약`](../../docs/03-backend/03-zod-contracts.md)
- [`서비스·저장소와 오류`](../../docs/03-backend/04-service-repository-errors.md)

## 작업하기

저장소 루트에서 실행하면 canonical `skeleton/`이 비덮어쓰기 방식으로 `work/`에 복사됩니다.

```sh
pnpm workspace:create 04-fastify-zod-api
pnpm --dir exercises/04-fastify-zod-api/work install
pnpm --dir exercises/04-fastify-zod-api/work test
```

## 구현할 계약

- 생성 본문은 공백을 정리하고 허용 길이를 검사합니다.
- route는 HTTP 변환, service는 업무 흐름, repository는 저장을 담당합니다.
- 존재하지 않는 자원은 404, 중복 계약 위반은 409로 응답합니다.
- 예상하지 못한 오류는 500으로 변환하되 스택·내부 열 이름을 응답하지 않습니다.
- 각 검사마다 독립 저장소와 Fastify 인스턴스를 만들고 종료합니다.
- `app.inject` 검사는 실제 route·hook·serializer를 지나갑니다.

## Reference 구현 순서

아래 번호는 역사적 작성 순서가 아니라 하나의 API reference가 공유하는 권장 construction order입니다. JSON config는 직접 주석하지 않고 bootstrap 책임을 이 표에 둡니다.

| 번호 | 위치 | 책임 |
|---:|---|---|
| [Implementation 0] | `pnpm install`, `package.json`, `tsconfig.json` | Fastify·Zod·TypeScript 실행 기반과 명령을 준비합니다. |
| 1 | `src/contracts.ts` | 외부 입력의 runtime schema와 내부 type contract를 만듭니다. |
| 2 | `src/repository.ts` | 저장 port와 instance별 memory state owner를 정의합니다. |
| 3 | `src/service.ts` | 제목 중복이라는 업무 invariant를 HTTP 밖에 둡니다. |
| 4 | `src/app.ts#buildApp` | app factory와 예상하지 못한 오류의 안정된 경계를 만듭니다. |
| 5 | `src/app.ts` 조회 route | 목록·단건 조회와 404 변환을 연결합니다. |
| 6 | `src/app.ts` 생성 route | body parse, service 호출과 409 변환을 연결합니다. |
| 7 | `src/server.ts` | repository를 주입하고 실제 listen을 시작하는 composition root를 둡니다. |

## 검증과 실패 주입

```sh
pnpm --dir exercises/04-fastify-zod-api/work typecheck
pnpm --dir exercises/04-fastify-zod-api/work test
pnpm --dir exercises/04-fastify-zod-api/work dev
```

다음 결함을 각각 만들었을 때 테스트가 실패해야 합니다.

- 본문을 `as CreateNoteInput`으로만 단언합니다.
- 없는 자원을 200과 `undefined`로 반환합니다.
- 중복을 500으로 뭉갭니다.
- repository를 모듈 전역 singleton으로 공유합니다.
- 내부 오류 객체를 그대로 JSON 응답에 넣습니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru exercises/04-fastify-zod-api/work exercises/04-fastify-zod-api/reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

정상 응답뿐 아니라 잘못된 JSON, 빈 제목, 없는 id, 중복과 내부 실패의 상태·응답 모양을 자동 검사합니다. 서버 종료 뒤 열린 handle이 남지 않아야 합니다.
