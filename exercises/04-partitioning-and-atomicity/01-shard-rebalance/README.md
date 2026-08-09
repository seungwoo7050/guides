# Shard rebalance 실습

## 목표

shard를 한 replica group에서 다른 group으로 옮기는 동안 write authority가 정확히 하나만 존재하도록 ownership, routing epoch와 fencing 상태 기계를 설계합니다.

## 입력

[`rebalance.json`](rebalance.json)은 range shard `S7`을 `G1`에서 `G2`로 옮기는 두 계획을 제공합니다.

- `safe-plan`: copy·catch-up·fence·cutover를 분리합니다.
- `unsafe-early-cutover`: target이 모든 변경을 따라잡기 전에 routing metadata를 전환합니다.

stale router는 이전 epoch로 source에 쓰기를 시도합니다.

## 작업

각 event 뒤 다음 상태를 갱신합니다.

```text
metadata_epoch
route owner
source phase / source applied_index / source write authority
target phase / target applied_index / target write authority
accepted writes and their durable location
```

다음을 판정합니다.

1. client write `w1`, `w2`, `w3`이 승인·redirect·retry·거절 중 무엇이어야 하는가
2. source가 write authority를 잃는 정확한 durable event
3. target이 authority를 얻기 전에 만족해야 하는 catch-up 조건
4. stale router와 stale source를 막는 epoch/fencing 검사가 어느 계층에 있어야 하는가
5. crash 뒤 migration을 재개할 때 정본으로 읽을 manifest

## 보존할 불변식

- 한 epoch에서 shard의 write authority는 하나입니다.
- 새 epoch를 durable하게 관찰한 old owner는 이전 epoch write를 적용하지 않습니다.
- cutover가 완료되기 전 source의 승인된 write는 target에 포함되거나 migration이 중단됩니다.
- target이 serving을 시작하기 전 snapshot과 delta의 적용 지점이 검증됩니다.
- cleanup은 routing cutover와 recovery 가능성이 확인된 뒤에만 실행됩니다.

## 대표 오답

- metadata service의 route만 바꾸고 old owner를 fencing하지 않습니다.
- snapshot copy 완료를 catch-up 완료로 간주합니다.
- source와 target이 잠시 둘 다 write를 받도록 한 뒤 last-write-wins로 합칩니다.
- client가 이전 epoch로 보낸 요청을 old owner가 새 owner로 무조건 전달해 중복 적용 가능성을 만듭니다.
- cleanup을 먼저 수행해 crash 뒤 복구할 source가 사라집니다.

## 완료 조건

- 두 계획의 event별 ownership 표를 제출합니다.
- `unsafe-early-cutover`에서 유실되거나 중복될 수 있는 write를 표시합니다.
- PREPARE, COPY, CATCH_UP, FENCE, CUTOVER, CLEANUP의 durable 상태와 재시작 행동을 정의합니다.
- stale router·source·target 각각에 대한 fencing 검사를 설계합니다.
