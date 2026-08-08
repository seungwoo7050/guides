# 04. HTTP API

## 목표

메모리 repository를 사용해도 완전한 HTTP 계약과 책임 경계를 가진 Fastify API를 만듭니다.

## 구현할 변경

- app factory와 실제 listen entry를 분리합니다.
- route는 HTTP 변환, service는 use case, repository는 저장을 담당합니다.
- 입력 schema, 응답 schema와 안정된 오류 body를 정의합니다.
- 인증 전 단계의 board CRUD와 activity 조회를 구현합니다.
- request id와 내부 원인은 log에 남기고 민감값은 가립니다.

## 실패 조건

- route가 SQL·권한·직렬화를 모두 처리합니다.
- 없는 자원을 200과 `undefined`로 반환합니다.
- 예상 가능한 충돌을 500으로 뭉갭니다.
- 전역 repository 때문에 테스트가 순서에 의존합니다.

## 검증

`app.inject`로 정상·잘못된 입력·없는 자원·충돌·예상하지 못한 오류를 확인하고, app을 반드시 닫습니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:04`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node checks/verify-work.mjs work 4
```

## 완료 계약

저장 구현을 PostgreSQL로 바꿔도 route와 전송 계약이 불필요하게 바뀌지 않습니다.
