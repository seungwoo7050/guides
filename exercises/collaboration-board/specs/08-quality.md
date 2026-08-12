# 08. 품질과 완료 증거

## 목표

형 검사, 단위·계약·API·DB·WebSocket·component·browser 검사와 production build를 서로 다른 증거로 구성합니다.

## 구현할 변경

- 순수 상태 변환과 좌표 제한은 단위 검사에 둡니다.
- runtime schema는 계약 검사에 둡니다.
- HTTP 상태·hook·직렬화는 `app.inject`로 검사합니다.
- constraint·경쟁·rollback은 실제 PostgreSQL에서 검사합니다.
- 두 WebSocket client와 reconnect를 통합 검사합니다.
- 로그인부터 보드 변경까지 핵심 흐름을 Playwright로 검사합니다.
- health/readiness, 구조화 log와 request/operation id를 추가합니다.

## 실패 조건

- 모든 위험을 하나의 긴 E2E에서만 검사합니다.
- 고정 sleep, 공유 고정 데이터와 CSS class selector에 의존합니다.
- production build를 `tsc`로 대체합니다.
- 성공 뒤 서버·pool·socket·browser를 정리하지 않습니다.

## 검증

새 checkout에서 install, typecheck, test, build, browser test가 문서화된 명령으로 재현되어야 합니다. 알려진 잘못된 구현을 넣었을 때 관련 검사가 실패하는지도 확인합니다.

검증 진입점은 다음과 같습니다. `work/package.json`의 `verify:08`는 이 단계까지의 형 검사·테스트·build를 누적 실행해야 합니다.

```sh
node exercises/collaboration-board/checks/verify-work.mjs exercises/collaboration-board/work 8
```

## 완료 계약

각 중요한 주장에 실행 가능한 증거가 있고, 실패 메시지로 문제 경계를 좁힐 수 있습니다.
