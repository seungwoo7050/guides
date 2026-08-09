# Client session과 snapshot 기대 결과

fixture는 counter 0과 `client-7`의 마지막 완료 sequence 2에서 시작합니다. 따라서 sequence 3은 gap이 아니라 다음 요청입니다.

## Safe snapshot

| Event | Counter | Session | 결과 |
|---|---:|---|---|
| e1 | 5 | seq 3, fingerprint `increment:5`, result 5 | effect 1회 |
| e2 | 5 | 변경 없음 | response만 유실 |
| e3 | 5 | 변경 없음 | cached result 5 반환 |
| e4 | 7 | seq 4, fingerprint `increment:2`, result 7 | effect 1회 |
| e5-e7 | 7 | seq 4가 snapshot에서 복원 | crash 뒤 의미 동일 |
| e8 | 7 | 변경 없음 | cached result 7 반환 |
| e9 | 7 | 변경 없음 | 같은 sequence의 다른 fingerprint를 충돌로 거절 |
| e10 | 7 | 변경 없음 | 이 reference의 contiguous 정책에서는 `SEQUENCE_GAP` |

## Unsafe snapshot

session table이 없는 snapshot에서 restart하면 sequence 3이 이미 적용됐다는 evidence가 사라집니다. e6을 새 요청처럼 적용하는 잘못된 구현은 counter를 5에서 10으로 만들며 at-most-once effect를 위반합니다.

## 사람 검토 질문

- duplicate result를 현재 state에서 다시 계산하지 않고 원래 result로 돌려줍니까?
- session update와 user state update가 같은 committed command로 apply됩니까?
- snapshot restore 뒤 fingerprint 충돌을 계속 판정할 수 있습니까?
- gap 허용 정책을 바꾼다면 out-of-order buffering과 recovery 의미를 함께 정의했습니까?

## 이 결과가 증명하지 않는 것

단일 client와 순차 sequence만 다룹니다. session GC, client incarnation, 여러 동시 client와 큰 response 저장 정책은 별도 검토가 필요합니다.
