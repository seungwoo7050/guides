# Realtime Board

Board별 snapshot, monotonic sequence, persistent patch, ephemeral preview, role authorization와 heartbeat cleanup을 제공하는 WebSocket server입니다. 단순 문자열 relay가 아니라 connection state와 optimistic concurrency를 명시적으로 소유하는 standalone realtime artifact입니다.

## Protocol

Client는 연결 직후 `board.join`을 보내야 합니다.

```json
{ "type": "board.join", "boardId": "planning" }
```

주요 inbound event:

| Event | Lifetime | Effect |
| --- | --- | --- |
| `board.join` | connection | room 확정과 snapshot 수신 |
| `snapshot.request` | request | 최신 snapshot 복구 |
| `cursor.move` | ephemeral | room 내 cursor broadcast, sequence 불변 |
| `item.create` | persistent | item 생성, board sequence 증가 |
| `item.update` | persistent | `baseVersion` 일치 시 content 변경 |
| `item.move final=false` | ephemeral | preview broadcast, DB/state 불변 |
| `item.move final=true` | persistent | 위치 저장, item version과 sequence 증가 |

Server outbound event는 `board.snapshot`, `board.patch`, `item.preview`, `cursor.moved`, `presence.changed`입니다. `board.patch`는 operation, sequence, board version과 변경된 item snapshot을 포함합니다.

## Install and run

```sh
pnpm install
pnpm typecheck
pnpm test
pnpm dev
```

기본 WebSocket endpoint는 `ws://localhost:4000/ws`입니다. `PORT`로 listener port를 변경할 수 있습니다.

## Architecture

```text
WebSocket frame
→ runtime protocol schema
→ connection and room hub
→ authorization boundary
→ BoardStore optimistic transition
→ snapshot, preview, or sequenced patch
```

`BoardStore`는 mutable board state를 단독 소유하고 외부에는 copy를 반환합니다. `ConnectionHub`는 socket, membership, presence와 room-scoped delivery를 소유합니다.

## Major design decisions

- Join 이전 event는 policy violation으로 connection을 닫습니다.
- 모든 inbound JSON은 Zod discriminated union으로 검증하고 좌표를 `1600×900` logical board 범위로 제한합니다.
- Viewer의 persistent write는 server에서 거부합니다.
- Stale `baseVersion`은 state를 변경하지 않고 현재 snapshot을 반환합니다.
- Preview와 cursor는 board sequence를 바꾸지 않습니다.
- Persistent transition만 item version, board version과 sequence를 전진시킵니다.
- Fastify close와 heartbeat timer·socket teardown을 같은 lifecycle에 묶습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | --- | --- |
| 1 | Runtime protocol contract | `src/protocol.ts` |
| 2 | Board state ownership | `src/state.ts` |
| 3 | Optimistic mutation boundary | `src/state.ts` |
| 4 | Connection and room hub | `src/hub.ts` |
| 5 | Realtime app composition | `src/app.ts` |
| 6 | Connection and join lifecycle | `src/app.ts` |
| 7 | Persistent-write authorization | `src/app.ts` |
| 8 | Snapshot, preview, and patch dispatch | `src/app.ts` |
| 9 | Heartbeat and teardown lifecycle | `src/app.ts` |
| 10 | Executable composition root | `src/server.ts` |

## Verification

Project tests cover malformed frames, coordinate bounds, join-before-use, room-wide patch equality, sequence recovery, preview non-persistence, stale-write rejection, viewer authorization and application teardown.

## Scope and limitations

State는 process memory에만 존재하고 logical board coordinate space는 `1600×900`으로 고정됩니다. Reconnect identity, durable persistence, horizontal fan-out, authentication, compression, rate limiting과 message replay buffer는 포함하지 않습니다. `snapshot.request.afterSequence`는 gap을 표현하지만 현재 구현은 항상 최신 full snapshot을 반환합니다.
