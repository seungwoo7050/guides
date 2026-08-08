# WebSocket 프로토콜

HTTP 요청은 한 번의 요청·응답으로 끝나지만 WebSocket은 연결이 오래 유지되고 양쪽이 언제든 메시지를 보낼 수 있습니다. 연결이 열렸다는 사실만으로 어떤 보드에 참여했는지, 마지막으로 어떤 상태를 봤는지, 현재 권한이 무엇인지 알 수 없습니다. 연결·세션·방·메시지의 상태를 명시적으로 관리해야 합니다.

## 목표

- HTTP upgrade와 WebSocket 연결 수명을 구분합니다.
- client·server 메시지를 판별 가능한 계약으로 정의합니다.
- 연결별 인증, 참가 상태와 정리 책임을 관리합니다.
- ping·pong, timeout, backpressure와 message limit을 적용합니다.
- 정상 종료·오류·재연결 뒤 상태 복구 흐름을 설명합니다.

## 연결 시작

browser는 HTTP 요청으로 upgrade를 요청합니다.

```text
GET /ws HTTP/1.1
Upgrade: websocket
Connection: Upgrade
Origin: https://app.example.com
Cookie: app_session=...
```

server는 upgrade 전에 다음을 확인합니다.

- 허용된 `Origin`
- session token과 만료
- 계정 상태
- 최대 연결 수와 server readiness

연결이 열린 뒤에도 아직 특정 보드 구성원이라고 가정하지 않습니다. client가 `board.join`을 보내면 server가 membership을 다시 확인하고 방 상태를 연결합니다.

## 메시지는 판별 가능한 union으로 만듭니다

```ts
const ClientMessageSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("board.join"),
    boardId: z.string().uuid()
  }),
  z.object({
    type: z.literal("cursor.move"),
    boardId: z.string().uuid(),
    x: z.number().finite(),
    y: z.number().finite()
  }),
  z.object({
    type: z.literal("item.move"),
    boardId: z.string().uuid(),
    itemId: z.string().uuid(),
    baseVersion: z.number().int().nonnegative(),
    x: z.number().finite(),
    y: z.number().finite(),
    final: z.boolean()
  })
]);
```

문자열을 JSON으로 해석하는 단계와 schema parse 단계를 분리합니다. 잘못된 한 message가 process 전체 예외나 다른 연결의 종료로 이어지지 않게 합니다.

## envelope 계약

장기적으로 message에는 업무 payload 외의 식별자가 필요할 수 있습니다.

```ts
interface Envelope<T> {
  type: string;
  messageId: string;
  sentAt: string;
  payload: T;
}
```

다음 식별자를 혼동하지 않습니다.

- `messageId`: 한 전송 메시지 추적
- `operationId`: 한 사용자 변경 시도 추적
- `itemId`: 업무 자원 식별
- `sequence`: 보드 안의 확정된 변경 순서
- `version`: 자원의 낙관적 동시성 번호

모든 값이 항상 필요한 것은 아닙니다. 복구와 중복 판정에 실제로 사용하는 항목만 계약에 넣습니다.

## 연결 상태

server는 socket 객체만 모으지 말고 연결 context를 가집니다.

```ts
interface ConnectionContext {
  socket: WebSocket;
  actorId: string;
  joinedBoardIds: Set<string>;
  alive: boolean;
  queuedBytes: number;
}
```

방 참가와 나가기를 한 함수에서 관리하고, socket 종료 시 모든 room index에서 제거합니다. room set에는 없는데 connection set에는 남은 ghost connection을 만들지 않습니다.

## 참가와 초기 상태

```text
연결 성공
→ client: board.join
→ server: session·membership 확인
→ server: board.snapshot
→ 이후 board.patch 수신
```

snapshot을 받기 전에 patch부터 적용하면 기준 상태가 없습니다. server는 join 처리 중 발생한 변경을 어떻게 순서화할지 정해야 합니다. 작은 구현은 snapshot을 만든 시점의 sequence를 함께 보내고 그 이후 patch만 적용하게 할 수 있습니다.

## 메시지 크기와 빈도

WebSocket은 긴 연결이므로 한 client가 큰 JSON이나 초당 수천 message로 자원을 소모할 수 있습니다.

- 최대 frame·message 크기
- 초당 message rate
- board별·사용자별 연결 수
- parse 전 raw byte limit
- 좌표 범위와 문자열 길이
- 압축 사용 시 메모리·CPU 영향

`cursor.move`처럼 빈번한 event는 최신 값만 의미가 있을 수 있습니다. 모든 중간 message를 queue에 쌓기보다 합치거나 drop할 정책을 둡니다.

## backpressure

socket의 송신 buffer가 계속 커지면 느린 client 하나가 server 메모리를 차지합니다.

```text
bufferedAmount가 임계값 미만 → 전송
일시 초과                   → ephemeral event drop 또는 pause
지속 초과                   → 연결 종료 후 재동기화
```

확정된 `board.patch`는 조용히 버리면 안 됩니다. 느린 client를 종료하고 재연결 snapshot으로 복구시키는 편이 명확할 수 있습니다. cursor 같은 임시 상태는 마지막 값만 유지할 수 있습니다.

## heartbeat

네트워크가 끊겨도 TCP 연결이 즉시 닫히지 않을 수 있습니다. server는 ping을 보내고 pong을 받은 연결만 alive로 표시합니다.

```text
주기 시작
→ 모든 연결 alive=false, ping
→ pong 수신 시 alive=true
→ 다음 주기에 false인 연결 종료
```

heartbeat timer는 server 종료과 test cleanup에서 반드시 정리합니다. application-level heartbeat를 사용한다면 protocol message와 WebSocket control frame의 역할을 구분합니다.

## 오류 메시지

잘못된 입력을 받은 뒤 모든 오류를 socket close로 처리할 필요는 없습니다.

```ts
{
  type: "operation.rejected",
  operationId: "...",
  code: "stale_item",
  message: "최신 상태를 다시 불러와 주세요."
}
```

반면 인증 만료, 신뢰하지 않은 origin, protocol 위반 반복과 message size 초과는 연결을 종료할 수 있습니다. close code와 client 재연결 가능 여부를 문서화합니다.

## 정상 종료

server 배포 시:

1. 새 upgrade 수락을 중단합니다.
2. client에 종료 예정 또는 reconnect signal을 보낼 수 있습니다.
3. 진행 중인 확정 작업을 제한된 시간 안에 마칩니다.
4. socket을 close합니다.
5. room index와 heartbeat timer를 정리합니다.
6. DB·HTTP server를 닫습니다.

강제 종료 전에 무한히 기다리지 않도록 shutdown deadline을 둡니다.

## 재연결

client는 연결이 끊긴 이유를 분류하고 제한된 지수 지연과 jitter로 다시 연결합니다.

```text
0.5초 → 1초 → 2초 → 4초 → 최대 간격
```

인증 실패나 명시적 접근 거부를 네트워크 오류처럼 무한 재시도하지 않습니다. 재연결 뒤 이전 메모리 상태를 그대로 믿지 않고 다시 join하고 snapshot을 받습니다.

## 실패 조건

- 연결 성공을 보드 참가와 같은 상태로 봅니다.
- JSON parse와 schema 실패를 process-level 예외로 만듭니다.
- socket 종료 후 room index에서 제거하지 않습니다.
- message 크기·빈도·송신 buffer 제한이 없습니다.
- heartbeat timer를 test와 shutdown에서 정리하지 않습니다.
- 재연결 뒤 이전 상태에서 patch만 계속 적용합니다.
- 인증 실패도 무한 재접속합니다.

## 연결 실습

[`WebSocket 스냅숏과 패치`](../../exercises/07-websocket/README.md)에서 join, snapshot, 두 연결 broadcast, heartbeat와 reconnect cleanup을 구현합니다.

## 완료 기준

- upgrade·connection·room 참가 상태를 구분합니다.
- client·server 메시지를 runtime schema로 검증합니다.
- 연결 context와 room index를 종료 시 완전히 정리합니다.
- heartbeat, message limit과 backpressure 정책을 설명합니다.
- 재연결 뒤 snapshot으로 상태를 복구합니다.

## 다음 단계

여러 client의 변경을 한 server 정본으로 수렴시키는 방법은 [`실시간 상태와 충돌`](02-realtime-state-conflicts.md)에서 다룹니다.
