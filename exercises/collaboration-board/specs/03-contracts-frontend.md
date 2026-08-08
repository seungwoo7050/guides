# 03. 공유 계약과 프런트엔드

## 목표

HTTP·WebSocket 전송 schema를 공유 package에 정의하고, Next.js 화면이 server·URL·component 상태를 구분해 사용하도록 만듭니다.

## 구현할 변경

- board, member, item, HTTP 요청·응답과 WebSocket message의 runtime schema를 만듭니다.
- 외부 값은 `unknown`에서 parse하고 형 단언만으로 신뢰하지 않습니다.
- Next.js App Router에 목록과 `/boards/[id]` 경로를 만듭니다.
- browser event와 effect가 필요한 가장 작은 component만 client component로 둡니다.
- API adapter를 화면에서 분리하고 loading·empty·error·ready를 표현합니다.
- 요청 cleanup과 오래된 응답 차단을 구현합니다.

## 실패 조건

- DB row type을 그대로 전송 계약으로 내보냅니다.
- 여러 component가 같은 server data를 독립 `useState`로 복사합니다.
- render 중 시각·storage를 읽어 hydration이 달라집니다.
- 느린 이전 요청이 최신 검색 결과를 덮습니다.

## 검증

잘못된 외부 값 거부, 빠른 연속 검색, component unmount, 동적 경로 직접 접근과 production build를 확인합니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:03`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node checks/verify-work.mjs work 3
```

## 완료 계약

프런트엔드는 전송 세부 구현이 아니라 adapter와 parse된 계약에 의존하고, UI 상태가 모순되지 않습니다.
