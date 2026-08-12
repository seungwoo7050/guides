# 테스트와 품질

모든 기능을 브라우저 시나리오 하나로 검사하면 느리고 실패 원인을 찾기 어렵습니다. 반대로 순수 함수 단위 검사만 많으면 실제 route, DB, browser와 WebSocket 경계가 깨져도 통과합니다. 각 위험이 처음 드러나는 가장 짧은 경계에 검사를 두고, 소수의 종단 간 흐름으로 조립 상태를 확인합니다.

## 목표

- 단위·계약·컴포넌트·API·DB·WebSocket·browser 검사의 역할을 구분합니다.
- 정상·실패·경계 조건을 결정적으로 재현합니다.
- test double과 실제 infrastructure 검사의 한계를 설명합니다.
- typecheck, test와 production build를 독립된 증거로 실행합니다.
- 품질 검사가 잘못된 구현을 실제로 거부하는지 확인합니다.

## 위험에서 검사 경계를 선택합니다

| 위험 | 가장 짧은 유효 검사 |
|---|---|
| 좌표 clamp·상태 전이 | 순수 단위 검사 |
| Zod schema가 잘못된 값 거부 | 계약 검사 |
| label·button·오류 알림 | 컴포넌트 또는 browser 검사 |
| Fastify hook·status·serialization | `app.inject` API 검사 |
| unique·foreign key·rollback | 실제 PostgreSQL 검사 |
| room broadcast·reconnect | 실제 WebSocket 두 연결 검사 |
| routing·hydration·keyboard·history | 실제 browser 검사 |
| server/client bundle 경계 | Next.js production build |

검사 이름은 구현 함수보다 업무 결과를 표현합니다.

```text
viewer는 메모 내용을 수정할 수 없다
같은 version의 두 저장 요청 중 하나만 성공한다
뒤로 가면 이전 검색 조건과 결과가 복원된다
```

## 단위 검사

부수 효과가 없는 규칙은 빠르고 다양한 입력으로 검사합니다.

```ts
it("보드 밖 좌표를 범위 안으로 제한한다", () => {
  expect(clampPoint({ x: -10, y: 900 }, { width: 800, height: 600 }))
    .toEqual({ x: 0, y: 600 });
});
```

현재 시각과 ID가 필요하면 `Clock`, `IdGenerator`를 입력으로 전달해 고정합니다. 내부 private 함수만 직접 검사하기 위해 구조를 깨지 말고 공개 업무 동작을 통해 확인합니다.

## 계약 검사

외부 입력과 출력 schema를 예시 몇 개로만 확인하지 않습니다.

- 필수 field 누락
- 잘못된 type
- 빈 문자열과 최대 길이
- 알 수 없는 discriminator
- non-finite number
- 추가 field 정책
- 이전·새 버전 payload의 호환성

response DTO도 parse해 비밀 열이 빠졌는지 확인합니다.

## 컴포넌트 검사

React Testing Library 계열에서는 역할과 이름으로 조작합니다.

```ts
await user.type(screen.getByLabelText("제목"), "회의 기록");
await user.click(screen.getByRole("button", { name: "저장" }));
expect(await screen.findByRole("status")).toHaveTextContent("저장됨");
```

CSS class와 component 내부 state를 직접 찾지 않습니다. 사용자가 접근할 수 없는 요소는 검사도 찾기 어렵게 만듭니다.

loading·empty·success·error를 각각 독립적으로 재현합니다. 느린 adapter, 거부되는 Promise와 빈 배열을 주입해 `sleep` 없이 상태를 고정합니다.

## API 검사

Fastify `app.inject`는 실제 listen port 없이 plugin, hook, route와 serialization을 실행합니다.

검사할 행렬:

- 올바른 요청과 status·body
- validation 400
- 인증 없음 401
- 권한 부족 403 또는 정책상 404
- 자원 없음 404
- uniqueness·version conflict 409
- 내부 오류 500과 stack 비노출
- request ID와 cookie header

각 검사마다 app을 만들고 종료하거나 suite 수명에 맞춰 명확히 close합니다.

## 실제 데이터베이스 검사

다음은 SQLite나 메모리 repository로 대체하지 않습니다.

- PostgreSQL migration 문법
- unique·foreign key·check constraint
- transaction rollback
- lock·isolation·concurrent update
- timestamp·JSON·numeric representation

전용 DB를 띄우고 migration을 빈 schema에 적용합니다. 검사 데이터는 고유 ID로 격리하고, transaction rollback 또는 명시적 cleanup을 사용합니다. process 종료 전에 pool을 닫습니다.

## WebSocket 검사

실제 server와 두 client를 사용합니다.

```text
client A·B 연결
→ 같은 board.join
→ 둘 다 snapshot
→ A가 item.move(final=true)
→ A·B가 같은 sequence patch
→ B reconnect
→ B가 최신 snapshot
```

메시지 배열의 첫 번째 값이라고 가정하지 말고 원하는 `type`, `operationId`, `sequence`를 기다리는 helper를 사용합니다. listener와 timeout은 성공·실패 양쪽에서 제거합니다.

잘못된 JSON, join 전 쓰기, viewer 쓰기, heartbeat timeout과 server shutdown도 검사합니다.

## Browser 검사

실제 browser만 증명할 수 있는 항목:

- keyboard focus와 native form 동작
- history와 URL
- CSS overflow와 viewport
- Next.js 직접 경로 접근·새로고침
- hydration과 client event
- cookie·CORS의 browser 동작
- Canvas pointer 좌표

Playwright 선택자는 role·label·text를 우선하고 고정 sleep을 사용하지 않습니다.

```ts
await expect(page.getByRole("heading", { name: "내 메모" })).toBeVisible();
```

브라우저 하나의 긴 시나리오보다 핵심 사용자 흐름을 독립적으로 만듭니다. 실패 시 trace·screenshot·server log를 남기되 cookie와 비밀값을 가립니다.

## 요청 순서 역전 검사

두 응답의 지연을 제어합니다.

```text
query=a     → 500ms
query=beta  → 100ms
```

사용자가 `a` 뒤 `beta`를 입력하면 최종 화면은 `beta` 결과여야 합니다. source에 `AbortController` 문자열이 있는지 찾지 말고 실제 화면 결과를 검사합니다.

## 낙관적 변경 검사

- UI가 즉시 바뀝니다.
- server 승인 patch로 pending이 해제됩니다.
- 409 conflict에서 이전 값 또는 최신 snapshot으로 복구합니다.
- 사용자가 입력한 draft를 잃지 않습니다.
- 중복 operation 응답이 효과를 두 번 적용하지 않습니다.

## Typecheck와 build

각 명령은 다른 문제를 잡습니다.

```text
typecheck → 정적 type·import 계약
test      → 실행 중 업무 동작
build     → framework compile·bundle·server/client 경계
E2E       → 실제 process와 browser 조립
```

`tsc --noEmit`이 통과해도 Next.js dynamic route와 server-only import가 production build에서 실패할 수 있습니다. build가 성공해도 권한과 rollback이 올바른 것은 아닙니다.

## 테스트의 품질을 검사합니다

검사가 항상 통과하는지 확인하려면 알려진 잘못된 구현을 주입합니다.

```text
label 제거
popstate handler 제거
version 조건 제거
logout session 폐기 제거
viewer write 허용
WebSocket listener cleanup 제거
```

각 mutation이 관련 검사를 실패시켜야 합니다. source 정규식만 검사하는 test보다 실제 외부 동작을 망가뜨린 fixture가 더 강한 근거입니다.

## 간헐적 실패 줄이기

- 고정 sleep 대신 관찰 가능한 결과를 기다립니다.
- clock·random·network 지연을 제어합니다.
- port 3000 같은 고정 공유 자원보다 빈 port를 할당합니다.
- 검사마다 고유 데이터 namespace를 사용합니다.
- server·timer·socket·DB pool·browser를 `finally`에서 정리합니다.
- 실패 메시지에 기대한 상태와 관찰한 상태를 포함합니다.

실패를 단순 재실행으로 숨기지 말고 재현 seed, trace와 resource leak를 찾습니다.

## 검증 피라미드보다 검증 포트폴리오

모든 프로젝트에 같은 비율을 강제하지 않습니다. 업무 위험에 맞게 구성합니다. DB 불변식이 핵심이면 실제 DB 검사가 많아지고, 접근성이 핵심이면 browser 검사가 중요합니다. 느린 검사 수를 줄이되 없어서는 안 될 경계를 mock으로 대체하지 않습니다.

## 실패 조건

- 모든 기능을 하나의 E2E 시나리오로만 검사합니다.
- 구현 세부 class·CSS selector에 검사 계약을 묶습니다.
- 실제 PostgreSQL·WebSocket 대신 mock만 사용합니다.
- 고정 `waitForTimeout`으로 동기화합니다.
- typecheck 하나를 runtime 검증으로 간주합니다.
- 검사 뒤 server·timer·socket·pool이 남습니다.
- 잘못된 구현도 통과하는지 확인하지 않습니다.

## 연결 실습

[`테스트 경계 비교`](../../exercises/08-testing/README.md)에서 같은 기능을 단위·API·browser에서 검사하고, 전체 계약은 [`실시간 협업 보드`](../06-capstones/04-collaboration-board.md)에서 조립합니다.

## 완료 기준

- 위험별로 가장 짧은 유효 검사 경계를 선택합니다.
- 정상·실패·경계·경쟁 조건을 결정적으로 재현합니다.
- 실제 DB·WebSocket·browser 검사가 필요한 항목을 구분합니다.
- typecheck·test·build·E2E를 독립된 증거로 실행합니다.
- 알려진 잘못된 구현이 검사를 실패시키는지 확인합니다.

## 다음 단계

먼저 [`테스트 경계 비교`](../../exercises/08-testing/README.md)의 생성된 `work/`에서 unit·API·browser 검사가 서로 다른 위험을 증명하는지 확인하고 완료 뒤 `reference/`와 비교합니다. Part 01에서 이미 브라우저 작업 목록을 수행했고 중간 notes brief는 선택 사항이므로, 다음 필수 단계는 runnable Stage 01–08의 최종 [`실시간 협업 보드`](../06-capstones/04-collaboration-board.md)입니다.
