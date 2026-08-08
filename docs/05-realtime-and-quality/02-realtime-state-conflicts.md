# 실시간 상태와 충돌

두 사용자가 같은 항목을 거의 동시에 움직이면 “마지막으로 도착한 좌표를 저장한다”는 규칙만으로는 사용자의 의도와 상태 복구를 설명하기 어렵습니다. 실시간 시스템은 모든 변경이 즉시 같은 순서로 보인다고 가정하지 않고, 임시 상태와 확정 상태, sequence와 version, snapshot과 patch를 조합해 결국 같은 정본으로 수렴해야 합니다.

## 목표

- server를 확정 상태의 권위자로 둡니다.
- snapshot·patch·sequence·version의 역할을 구분합니다.
- 임시 움직임과 영속 변경을 다른 계약으로 처리합니다.
- 오래된 요청, 중복·누락·순서 역전에서 복구합니다.
- 낙관적 UI가 실패했을 때 사용자에게 되돌림·재시도 경로를 제공합니다.

## 상태를 세 종류로 나눕니다

```text
영속 상태   → 항목 내용·최종 좌표·version, DB 정본
임시 상태   → cursor·drag 중 좌표, server memory
화면 상태   → 선택·hover·dialog·draft, client local
```

모든 pointer move를 DB에 저장하면 write와 활동 기록이 폭증합니다. 반대로 최종 좌표까지 memory에만 두면 reconnect와 server restart 뒤 사라집니다.

## snapshot과 patch

snapshot은 특정 시점의 전체 복구 기준입니다.

```ts
interface BoardSnapshot {
  boardId: string;
  sequence: number;
  version: number;
  items: BoardItem[];
}
```

patch는 그 이후의 확정 변경입니다.

```ts
interface BoardPatch {
  boardId: string;
  sequence: number;
  operationId: string;
  actorId: string;
  operation: ItemCreated | ItemUpdated | ItemMoved;
}
```

client는 snapshot의 `sequence`를 마지막 적용 순서로 저장합니다.

## sequence로 누락과 중복을 찾습니다

patch의 sequence가 `lastSequence + 1`이면 적용합니다.

```text
sequence <= lastSequence     → 중복 또는 오래된 patch, 무시
sequence == lastSequence + 1 → 적용
sequence > lastSequence + 1  → 누락, patch 적용 중단 후 snapshot 요청
```

sequence가 transport 도착 순서가 아니라 server가 확정한 보드 변경 순서여야 합니다. 여러 server instance에서 단조 순서를 어떻게 생성할지는 DB counter, sequence 또는 partition owner 같은 설계가 필요합니다.

## version은 자원 충돌을 찾습니다

사용자가 item version 4를 보고 수정했다면 `baseVersion: 4`를 보냅니다. server는 DB의 현재 version이 4일 때만 version 5로 갱신합니다.

```sql
update board_items
set x = $1,
    y = $2,
    version = version + 1
where id = $3 and version = $4
returning *;
```

행이 없으면 stale write입니다. server가 client 값을 강제로 덮지 않고 conflict code와 최신 snapshot 또는 item을 제공합니다.

sequence와 version은 다릅니다.

- sequence: 보드 전체 변경 흐름의 누락·순서
- version: 특정 자원의 stale write

## drag 중과 완료

```text
pointermove
→ client가 빈도 제한
→ item.move(final=false)
→ server가 좌표 clamp
→ 방에 임시 broadcast

pointerup
→ item.move(final=true, baseVersion)
→ DB 조건부 update + event append transaction
→ 확정 board.patch broadcast
```

임시 좌표를 받은 다른 client는 그 항목의 preview만 바꿉니다. 확정 patch가 오면 영속 상태를 갱신하고 preview를 제거합니다.

client가 drag 중 disconnect되면 임시 상태는 timeout으로 제거하고 DB의 마지막 확정 좌표가 남습니다.

## 낙관적 UI

client는 응답 전 자신의 변경을 화면에 적용할 수 있습니다. 각 operation을 추적합니다.

```ts
interface PendingOperation {
  operationId: string;
  itemId: string;
  baseVersion: number;
  optimisticValue: unknown;
  previousValue: unknown;
}
```

server가 같은 `operationId`의 확정 patch를 보내면 pending을 완료합니다. 거부되면 previous value로 되돌리거나 최신 snapshot을 적용하고 사용자에게 재시도 선택을 제공합니다.

낙관적 변경을 단순히 “실패하면 refetch”로만 처리하면 입력 내용이 사라질 수 있습니다. draft와 server state를 분리해 충돌 내용을 보여 줄 수 있습니다.

## 중복 작업

network retry나 reconnect로 같은 operation이 다시 올 수 있습니다. operation ID를 일정 범위에서 기억해 같은 업무 효과를 두 번 만들지 않게 할 수 있습니다.

```text
처음 operationId → 처리하고 결과 저장
같은 operationId → 이전 결과 반환 또는 동일 patch 재전송
다른 payload와 같은 ID → protocol error
```

모든 cursor event에 영구 idempotency 기록이 필요하지는 않습니다. 결제처럼 강한 효과와 달리 board edit의 범위·보존 기간을 명확히 정합니다.

## 늦은 patch와 재연결

client가 offline 동안 여러 변경이 발생했으면 다음 두 방식이 있습니다.

- 마지막 sequence 이후 event를 보관해 gap replay
- 항상 최신 snapshot 재전송

작은 가이드에서는 snapshot 복구가 단순하고 안전합니다. 데이터가 커지면 snapshot 크기, replay retention과 compaction을 고려합니다.

## 삭제와 tombstone

항목 삭제 patch 뒤 늦은 update가 도착할 수 있습니다. server는 삭제된 항목을 다시 만들지 않게 current state와 version을 확인합니다. replay가 필요하면 tombstone 또는 delete event를 일정 기간 보존할 수 있습니다.

## 시간은 순서가 아닙니다

client의 `Date.now()`나 서로 다른 server clock으로 전체 변경 순서를 정하지 않습니다. timestamp는 표시·감사에 유용하지만 network 지연과 clock skew가 있습니다. 업무 순서는 server sequence와 transaction 결과를 사용합니다.

## 권한 변화

연결 중 사용자의 role이 editor에서 viewer로 바뀔 수 있습니다.

- membership 변경을 확정 state로 저장합니다.
- 해당 방에 role change patch 또는 새 snapshot을 보냅니다.
- 이후 모든 쓰기 message에서 현재 권한을 확인합니다.
- 진행 중 낙관적 변경은 거부되고 client가 되돌립니다.

연결 당시 role만 connection context에 영구 고정하지 않습니다.

## 실패 조건

- client가 최종 상태의 정본입니다.
- sequence와 item version을 같은 값으로 사용합니다.
- drag 중 모든 좌표를 DB와 감사 기록에 저장합니다.
- gap이 있어도 patch를 계속 적용합니다.
- stale write를 마지막 도착 값으로 덮습니다.
- 낙관적 변경 실패 시 사용자 draft를 조용히 버립니다.
- timestamp를 전체 순서로 사용합니다.

## 연결 실습

[`WebSocket 스냅숏과 패치`](../../exercises/07-websocket/README.md)에서 두 연결, snapshot, patch와 reconnect를 확인하고, [`실시간 협업 보드`](../06-capstones/04-collaboration-board.md)에서 DB version과 결합합니다.

## 완료 기준

- 영속·임시·화면 상태의 정본을 구분합니다.
- snapshot·patch·sequence·version의 서로 다른 역할을 설명합니다.
- 누락·중복·순서 역전과 stale write에서 복구합니다.
- drag preview와 최종 transaction을 분리합니다.
- 낙관적 UI의 승인·거부·되돌림 상태를 모델링합니다.

## 다음 단계

확정 상태를 고성능의 imperative 화면에 그리되 소유권을 섞지 않는 방법은 [`Canvas 렌더링`](03-canvas-rendering.md)에서 다룹니다.
