# WebSocket 스냅숏, 패치와 재연결

작은 서버에서 보드 참가, 스냅숏, 순서가 있는 패치, 권한, heartbeat와 재연결 복구를 구현합니다. WebSocket은 단순한 양방향 문자열 통로가 아니라 연결 상태를 오래 유지하는 프로토콜이라는 점을 확인합니다.

## 선행 문서

- [`WebSocket 프로토콜`](../../docs/05-realtime-and-quality/01-websocket-protocol.md)
- [`실시간 상태와 충돌`](../../docs/05-realtime-and-quality/02-realtime-state-conflicts.md)

## 작업하기

저장소 루트에서 실행하면 canonical `skeleton/`이 비덮어쓰기 방식으로 `work/`에 복사됩니다.

```sh
pnpm workspace:create 07-websocket
pnpm --dir exercises/07-websocket/work install
pnpm --dir exercises/07-websocket/work test
```

## 구현할 계약

- 연결 직후에는 변경을 허용하지 않고 `board.join` 성공 뒤에만 room에 참여시킵니다.
- 모든 JSON은 실행 시점 스키마로 검사합니다.
- 참가자는 현재 `board.snapshot`을 받고 이후 증가하는 `sequence`의 `board.patch`를 받습니다.
- 같은 보드의 두 연결은 같은 영속 패치를 받습니다.
- 읽기 전용 역할은 cursor/presence 외의 쓰기를 할 수 없습니다.
- sequence gap이나 오래된 baseVersion은 최신 snapshot으로 복구합니다.
- ping/pong timeout, listener, timer와 socket은 성공·실패·서버 종료에서 정리됩니다.

## Reference 구현 순서

아래 번호는 역사적 작성 순서가 아니라 protocol과 server 파일이 공유하는 권장 construction order입니다. JSON config는 직접 주석하지 않고 이 표가 bootstrap 책임을 설명합니다.

| 번호 | 위치 | 책임 |
|---:|---|---|
| [Implementation 0] | `pnpm install`, `package.json`, `tsconfig.json` | Fastify WebSocket·Zod·TypeScript 실행 기반을 준비합니다. |
| 1 | `src/protocol.ts` | 신뢰하지 않는 client message schema와 server event contract를 정의합니다. |
| 2 | `src/app.ts` state model | client·board state의 owner와 connection role을 정합니다. |
| 3 | `/ws` handler | parse, join-before-write와 connection listener lifecycle을 연결합니다. |
| 4 | board·presence helpers | room별 snapshot과 참여자 projection을 관리합니다. |
| 5 | viewer guard | 읽기 전용 역할의 영속 쓰기를 server에서 거부합니다. |
| 6 | item creation | 새 항목과 board version·sequence를 함께 전진시킵니다. |
| 7 | item update·move | stale version 복구, transient preview와 final persistence를 분리합니다. |
| 8 | heartbeat·onClose | timer와 모든 socket을 app lifecycle에 묶습니다. |
| 9 | `src/server.ts` | app을 완성한 뒤 network listen을 시작합니다. |

## 검증과 실패 주입

```sh
pnpm --dir exercises/07-websocket/work typecheck
pnpm --dir exercises/07-websocket/work test
pnpm --dir exercises/07-websocket/work dev
```

다음을 하나씩 깨뜨려 테스트가 실제로 실패하는지 확인합니다.

- 잘못된 JSON을 예외 처리 없이 해석합니다.
- join 전 변경을 허용합니다.
- 모든 연결에 다른 board의 패치를 broadcast합니다.
- heartbeat timer를 종료하지 않습니다.
- 재연결 뒤 이전 메모리 상태를 그대로 신뢰합니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru exercises/07-websocket/work exercises/07-websocket/reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

두 실제 client의 참가·broadcast·권한 거부·재연결을 검사하고, 열린 socket이나 timer 때문에 테스트 프로세스가 남지 않아야 합니다.
