# Shard rebalance 기대 결과

## Safe plan

e1-e6 동안 metadata epoch 21의 owner는 G1입니다. snapshot index 120 뒤 승인된 w1·w2는 source index 121·122에 기록되고 target도 delta를 index 122까지 적용합니다.

e7의 durable source fence가 G1의 write authority를 먼저 제거합니다. 이 시점부터 cutover 전까지 잠시 write 가능한 owner가 없는 것은 허용되지만, 둘이 동시에 write authority를 갖는 것은 허용되지 않습니다. e8은 target frontier 122를 확인한 뒤 epoch 22의 owner를 G2로 publish하고, e9 뒤 G2가 write를 받습니다.

stale router가 e10에서 G1에 보낸 w3은 적용하지 않고 epoch 22 route로 retry하도록 응답해야 합니다. e11의 retry만 G2 index 123에 한 번 적용됩니다. cleanup은 source fence, metadata cutover와 target serving이 durable하게 확인된 뒤 수행합니다.

## Unsafe early cutover

target은 index 120까지만 가진 상태에서 serving을 시작합니다. source에서 승인된 w1(index 121)이 빠진 채 target의 w2도 local index 121을 사용합니다. 늦은 delta는 같은 logical position의 다른 write와 충돌하거나 w1을 유실시킵니다. last-write-wins는 authority·acknowledgement 계약을 복구하지 못합니다.

## 사람 검토 질문

- metadata route와 storage owner의 fencing을 별도 상태로 추적했습니까?
- source fence 뒤 target enable 전의 no-writer window를 retry 가능한 availability 손실로 설명했습니까?
- crash 뒤 `migration_id`, epoch, base/final index를 어느 durable manifest에서 읽습니까?
- stale source, target과 router 각각 어느 계층에서 epoch를 검사합니까?

## 이 결과가 증명하지 않는 것

한 range와 하나의 순차 delta stream만 모델링합니다. multi-range transaction, split/merge, concurrent migration, storage checksum과 실제 cleanup 비용은 다루지 않습니다.
