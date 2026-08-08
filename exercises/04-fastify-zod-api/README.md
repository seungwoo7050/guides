# Fastify와 Zod API

외부 요청을 `unknown`으로 취급하고 실행 시점에 검증합니다. route, service, repository의 책임을 나누고 400·404·409와 내부 오류를 안정적으로 구분합니다.

## 선행 문서

- [`HTTP API 모델`](../../docs/03-backend/01-http-api-model.md)
- [`Fastify 생명주기`](../../docs/03-backend/02-fastify-lifecycle.md)
- [`Zod 전송 계약`](../../docs/03-backend/03-zod-contracts.md)
- [`서비스·저장소와 오류`](../../docs/03-backend/04-service-repository-errors.md)

## 작업하기

```sh
cd exercises/04-fastify-zod-api
rm -rf work
cp -R skeleton work
cd work
pnpm install
pnpm test
```

## 구현할 계약

- 생성 본문은 공백을 정리하고 허용 길이를 검사합니다.
- route는 HTTP 변환, service는 업무 흐름, repository는 저장을 담당합니다.
- 존재하지 않는 자원은 404, 중복 계약 위반은 409로 응답합니다.
- 예상하지 못한 오류는 500으로 변환하되 스택·내부 열 이름을 응답하지 않습니다.
- 각 검사마다 독립 저장소와 Fastify 인스턴스를 만들고 종료합니다.
- `app.inject` 검사는 실제 route·hook·serializer를 지나갑니다.

## 검증과 실패 주입

```sh
pnpm typecheck
pnpm test
pnpm dev
```

다음 결함을 각각 만들었을 때 테스트가 실패해야 합니다.

- 본문을 `as CreateNoteInput`으로만 단언합니다.
- 없는 자원을 200과 `undefined`로 반환합니다.
- 중복을 500으로 뭉갭니다.
- repository를 모듈 전역 singleton으로 공유합니다.
- 내부 오류 객체를 그대로 JSON 응답에 넣습니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru work reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

정상 응답뿐 아니라 잘못된 JSON, 빈 제목, 없는 id, 중복과 내부 실패의 상태·응답 모양을 자동 검사합니다. 서버 종료 뒤 열린 handle이 남지 않아야 합니다.
