# 테스트 경계 비교

같은 카운터 기능을 순수 함수, Fastify 주입과 실제 브라우저에서 검사합니다. 테스트 개수를 늘리는 것이 아니라 각 위험을 가장 짧고 정확하게 드러내는 경계를 선택하는 연습입니다.

## 선행 문서

- [`테스트와 품질`](../../docs/05-realtime-and-quality/04-testing-quality.md)

## 작업하기

저장소 루트에서 실행하면 canonical `skeleton/`이 비덮어쓰기 방식으로 `work/`에 복사됩니다.

```sh
pnpm workspace:create 08-testing
pnpm --dir exercises/08-testing/work install
pnpm --dir exercises/08-testing/work typecheck
pnpm --dir exercises/08-testing/work test
pnpm --dir exercises/08-testing/work exec playwright install chromium
pnpm --dir exercises/08-testing/work test:e2e
```

## 비교할 위험

| 위험 | 가장 먼저 둘 검사 |
|---|---|
| 감소 계산의 경계값 | 순수 함수 단위 검사 |
| HTTP 상태·직렬화·hook | `app.inject` API 검사 |
| 버튼의 접근 가능한 이름과 실제 사용자 흐름 | 브라우저 검사 |
| 서버와 브라우저 정리 누락 | 통합 검사 종료 상태 |

## Reference 구현 순서

아래 번호는 역사적 작성 순서가 아니라 production code와 learner-authored test가 공유하는 권장 construction order입니다. 이 실습은 테스트 구현 자체가 학습 목표이므로 `reference/`의 test와 Playwright config도 annotation 대상입니다. JSON config는 이 표에서만 설명합니다.

| 번호 | 위치 | 책임 |
|---:|---|---|
| [Implementation 0] | `pnpm install`, `package.json`, `tsconfig.json` | Fastify·Vitest·Playwright·TypeScript 실행 기반과 test 명령을 준비합니다. |
| 1 | `src/counter.ts` | framework와 무관한 순수 상태 전이를 만듭니다. |
| 2 | `src/counter.test.ts` | 경계값을 가장 작은 unit test에서 증명합니다. |
| 3 | `src/app.ts` | 순수 함수를 HTTP와 접근 가능한 HTML에 연결합니다. |
| 4 | `src/app.test.ts` | `app.inject`로 HTTP 계약과 app cleanup을 검증합니다. |
| 5 | `src/server.ts` | 실행 가능한 server entry와 port ownership을 만듭니다. |
| 6 | `playwright.config.ts` | 실행별 port, web server와 browser test lifecycle을 구성합니다. |
| 7 | `tests/counter.spec.ts` | role·name selector와 관찰 가능한 UI 결과로 사용자 흐름을 증명합니다. |

## 실패 주입

1. 감소 함수가 0 아래로 내려가게 만듭니다.
2. route 경로를 바꿉니다.
3. 버튼의 보이는 텍스트와 접근 가능한 이름을 제거합니다.
4. 관찰 가능한 결과 대신 `waitForTimeout`을 넣습니다.
5. CSS class 선택자로 브라우저 검사를 바꿉니다.
6. 서버 종료를 제거해 열린 handle을 남깁니다.

각 결함에 대해 어느 검사가 가장 짧은 실패 메시지를 주는지 기록합니다. 동일한 동작을 모든 층에서 중복 검사하지 않습니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru exercises/08-testing/work exercises/08-testing/reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

- 단위, API, 브라우저 검사가 서로 다른 계약을 확인합니다.
- 현재 시각·무작위 값과 고정 대기 때문에 간헐적으로 실패하지 않습니다.
- 브라우저 선택자는 역할, 이름과 label을 우선합니다.
- 성공과 실패 양쪽에서 서버·listener·timer·browser가 정리됩니다.
- 각 테스트가 실패했을 때 원인을 좁힐 수 있는 메시지를 제공합니다.
