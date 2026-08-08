# 프런트엔드 실무 점검표

이 문서는 본문의 대체물이 아니다. 구현·리뷰·장애 분석에서 이번 변경과 관련된 항목만 골라 확인한다.

## 프로젝트 합류

- [ ] `.nvmrc`, `engines`, `packageManager`와 lockfile을 확인했다.
- [ ] 고정 설치, typecheck, unit test, build, E2E와 smoke 명령을 찾았다.
- [ ] development server와 production server를 각각 실행했다.
- [ ] URL에서 page, data function, client boundary, command와 test까지 추적했다.
- [ ] server·browser·build 시점의 실행 위치를 구분했다.
- [ ] server-only 환경 변수와 browser-public 환경 변수를 구분했다.
- [ ] 기존 CI가 실제로 실행하는 명령을 확인했다.

## 기능 계약

- [ ] 사용자, 조건, 행동과 관찰 결과를 한 문장으로 적었다.
- [ ] 입력·출력·실패·시간 계약을 적었다.
- [ ] 첫 변경을 하나의 수직 기능으로 제한했다.
- [ ] 정상, 빈 결과와 대표 실패를 구분했다.
- [ ] reload와 back/forward 뒤 복원할 상태를 정했다.
- [ ] 요청 순서와 중복 command 가능성을 검토했다.

## 상태 소유권

- [ ] URL state는 URL과 history가 소유한다.
- [ ] server state를 여러 client store에 불필요하게 복제하지 않았다.
- [ ] 사용자가 편집 중인 draft와 server 확정 값을 분리했다.
- [ ] 계산 가능한 값은 render 중 계산한다.
- [ ] 배타적인 UI 상태를 discriminated union으로 제한했다.
- [ ] pending과 error에서 이전 데이터를 유지할지 명시했다.
- [ ] 새로 고침·navigation·사용자 전환 때 지울 상태를 정했다.

## Server·Client 경계

- [ ] 비밀값·데이터 접근·첫 표현을 server에 둘 수 있는지 검토했다.
- [ ] `"use client"` 범위를 실제 상호작용이 필요한 곳으로 제한했다.
- [ ] client boundary를 넘는 props는 직렬화 가능하다.
- [ ] server-only module이 client graph에 포함되지 않는다.
- [ ] 내부 server function을 불필요하게 자신의 Route Handler로 HTTP 호출하지 않는다.
- [ ] loading·error·not-found 경계에 사용자의 다음 행동이 있다.

## 외부 데이터

- [ ] URL, HTTP, storage와 message 입력을 `unknown`에서 검증한다.
- [ ] TypeScript assertion을 runtime validation으로 오해하지 않는다.
- [ ] duplicate id, 음수·과대 값과 알 수 없는 enum을 처리한다.
- [ ] API 응답을 component 이전의 한 경계에서 화면 모델로 바꾼다.
- [ ] malformed 성공 응답을 화면 state에 반영하지 않는다.
- [ ] user-facing message와 diagnostic detail을 분리한다.

## 요청과 효과

- [ ] 새 요청은 이전 signal을 abort한다.
- [ ] 결과 반영 전에 최신 generation인지 확인한다.
- [ ] 사용자 취소, timeout, HTTP 실패, contract 실패를 구분한다.
- [ ] stale result는 조용히 폐기한다.
- [ ] effect에는 외부 대상·재실행 조건·cleanup이 보인다.
- [ ] render 중 계산 가능한 값을 effect로 다시 저장하지 않는다.
- [ ] unmount 뒤 요청과 구독이 정리된다.

## 변경 작업과 충돌

- [ ] optimistic update 전에 이전 server state를 보관한다.
- [ ] 성공 응답의 server 보정 값과 새 version을 사용한다.
- [ ] 일반 실패에서 server state를 rollback하고 draft를 보존한다.
- [ ] 409 conflict에서 최신 server value와 local draft를 함께 보존한다.
- [ ] 저장 중 중복 제출 정책이 있다.
- [ ] conflict, permission failure와 network failure를 다른 문장으로 설명한다.
- [ ] 사용자가 입력을 복구하거나 다시 제출할 경로가 있다.

## 접근성

- [ ] navigation에는 link, action에는 button을 사용한다.
- [ ] 모든 form control에 연결된 이름이 있다.
- [ ] icon-only button에 accessible name이 있다.
- [ ] heading, main, form, list와 article 구조가 논리적이다.
- [ ] loading·failure·save 결과가 live region에 전달된다.
- [ ] keyboard만으로 검색과 편집을 완료할 수 있다.
- [ ] editor open, cancel, success, failure와 conflict의 focus 위치를 정했다.
- [ ] focus-visible indicator가 실제 computed style에서 보인다.
- [ ] 상태를 색 하나로만 구분하지 않는다.

## Responsive UI

- [ ] 320px에서 주요 작업과 text가 잘리지 않는다.
- [ ] 200% 확대에서 horizontal page overflow가 없다.
- [ ] 공백 없는 긴 title과 큰 글자에서 article이 넘치지 않는다.
- [ ] input, select와 flex/grid child에 필요한 `min-width: 0`이 있다.
- [ ] image와 font의 공간을 예약한다.
- [ ] reduced motion preference를 실제 computed style로 확인했다.

## 검사

- [ ] 가장 큰 위험과 그 검사를 먼저 적었다.
- [ ] parser, state와 coordinator는 DOM 없이 검사한다.
- [ ] network response 순서를 고정 sleep 없이 제어한다.
- [ ] 예상하지 않은 application request를 발견한다.
- [ ] production build 뒤 production server로 browser test한다.
- [ ] cookie, storage, server fixture와 route mock을 test 사이에 격리한다.
- [ ] 실패 trace, screenshot, console과 server output을 보존한다.
- [ ] retry로 결정적인 실패를 숨기지 않는다.

## 성능

- [ ] 변경 전 budget 또는 baseline이 있다.
- [ ] 초기 route의 JavaScript body byte를 비교한다.
- [ ] DOM node가 기능 크기에 비해 급증하지 않았다.
- [ ] 작은 interaction 때문에 client boundary가 넓어지지 않았다.
- [ ] optional feature와 큰 library가 초기 route에 들어오지 않는다.
- [ ] memoization은 측정한 병목과 안정성 요구가 있을 때만 사용한다.
- [ ] 실제 사용자 지표를 배포 전후로 연결할 방법이 있다.

## 운영 계약

- [ ] 고정 설치·build·start command가 문서화되어 있다.
- [ ] health endpoint는 작고 안정되며 `no-store`다.
- [ ] release identifier를 health와 error에서 찾을 수 있다.
- [ ] test-only endpoint는 test mode와 token 없이는 닫힌다.
- [ ] server-only secret canary가 HTML·health·초기 JS에 없다.
- [ ] standalone smoke는 고유 port와 timeout을 사용한다.
- [ ] smoke 성공·실패 뒤 child process가 남지 않는다.
- [ ] application contract와 infrastructure 실행 책임을 구분했다.

## 장애를 좁히는 순서

1. 같은 URL, 사용자, 입력과 release에서 재현되는지 확인한다.
2. development와 production build 결과를 비교한다.
3. server render, client hydration, event 이후 중 어느 시점부터 다른지 찾는다.
4. URL과 local draft, server response가 각각 예상한 값인지 확인한다.
5. HTTP method, URL, status, body contract와 timing을 확인한다.
6. stale response, duplicate command와 conflict 가능성을 확인한다.
7. 상태는 맞지만 DOM·CSS·focus 표현만 잘못됐는지 분리한다.
8. request ID와 release identifier로 browser와 server 증거를 연결한다.
9. 한 경계만 바꾸고 같은 조건에서 다시 실행한다.
10. 수정 뒤 해당 계층 검사와 핵심 production browser flow를 다시 통과한다.
