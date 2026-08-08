# WebSocket 스냅숏, 패치와 재연결

작은 서버에서 보드 참가, 스냅숏, 순서가 있는 패치, 권한, heartbeat와 재연결 복구를 구현합니다. WebSocket은 단순한 양방향 문자열 통로가 아니라 연결 상태를 오래 유지하는 프로토콜이라는 점을 확인합니다.

## 선행 문서

- [`WebSocket 프로토콜`](../../docs/05-realtime-and-quality/01-websocket-protocol.md)
- [`실시간 상태와 충돌`](../../docs/05-realtime-and-quality/02-realtime-state-conflicts.md)

## 작업하기

```sh
cd exercises/07-websocket
rm -rf work
cp -R skeleton work
cd work
pnpm install
pnpm test
```

## 구현할 계약

- 연결 직후에는 변경을 허용하지 않고 `board.join` 성공 뒤에만 room에 참여시킵니다.
- 모든 JSON은 실행 시점 스키마로 검사합니다.
- 참가자는 현재 `board.snapshot`을 받고 이후 증가하는 `sequence`의 `board.patch`를 받습니다.
- 같은 보드의 두 연결은 같은 영속 패치를 받습니다.
- 읽기 전용 역할은 cursor/presence 외의 쓰기를 할 수 없습니다.
- sequence gap이나 오래된 baseVersion은 최신 snapshot으로 복구합니다.
- ping/pong timeout, listener, timer와 socket은 성공·실패·서버 종료에서 정리됩니다.

## 검증과 실패 주입

```sh
pnpm typecheck
pnpm test
pnpm dev
```

다음을 하나씩 깨뜨려 테스트가 실제로 실패하는지 확인합니다.

- 잘못된 JSON을 예외 처리 없이 해석합니다.
- join 전 변경을 허용합니다.
- 모든 연결에 다른 board의 패치를 broadcast합니다.
- heartbeat timer를 종료하지 않습니다.
- 재연결 뒤 이전 메모리 상태를 그대로 신뢰합니다.

## Reference 비교

자동 검증을 모두 통과한 뒤에만 `diff -ru work reference`로 구현을 비교합니다. 파일 배치나 표현이 달라도 계약을 만족하면 올바른 구현이며, 차이를 선택한 이유를 설명합니다.

## 완료 기준

두 실제 client의 참가·broadcast·권한 거부·재연결을 검사하고, 열린 socket이나 timer 때문에 테스트 프로세스가 남지 않아야 합니다.
