# 테스트 경계 비교

같은 카운터 기능을 순수 함수, Fastify 주입과 실제 브라우저에서 검사합니다. 테스트 개수를 늘리는 것이 아니라 각 위험을 가장 짧고 정확하게 드러내는 경계를 선택하는 연습입니다.

## 선행 문서

- [`테스트와 품질`](../../docs/05-realtime-and-quality/04-testing-quality.md)

## 작업하기

```sh
cd exercises/08-testing
rm -rf work
cp -R skeleton work
cd work
pnpm install
pnpm typecheck
pnpm test
pnpm exec playwright install chromium
pnpm test:e2e
```

## 비교할 위험

| 위험 | 가장 먼저 둘 검사 |
|---|---|
| 감소 계산의 경계값 | 순수 함수 단위 검사 |
| HTTP 상태·직렬화·hook | `app.inject` API 검사 |
| 버튼의 접근 가능한 이름과 실제 사용자 흐름 | 브라우저 검사 |
| 서버와 브라우저 정리 누락 | 통합 검사 종료 상태 |

## 실패 주입

1. 감소 함수가 0 아래로 내려가게 만듭니다.
2. route 경로를 바꿉니다.
3. 버튼의 보이는 텍스트와 접근 가능한 이름을 제거합니다.
4. 관찰 가능한 결과 대신 `waitForTimeout`을 넣습니다.
5. CSS class 선택자로 브라우저 검사를 바꿉니다.
6. 서버 종료를 제거해 열린 handle을 남깁니다.

각 결함에 대해 어느 검사가 가장 짧은 실패 메시지를 주는지 기록합니다. 동일한 동작을 모든 층에서 중복 검사하지 않습니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru work reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

- 단위, API, 브라우저 검사가 서로 다른 계약을 확인합니다.
- 현재 시각·무작위 값과 고정 대기 때문에 간헐적으로 실패하지 않습니다.
- 브라우저 선택자는 역할, 이름과 label을 우선합니다.
- 성공과 실패 양쪽에서 서버·listener·timer·browser가 정리됩니다.
- 각 테스트가 실패했을 때 원인을 좁힐 수 있는 메시지를 제공합니다.
