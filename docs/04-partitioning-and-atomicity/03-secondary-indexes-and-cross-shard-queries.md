# Secondary index와 cross-shard query

## 목표

primary key routing으로 찾을 수 없는 query를 여러 shard에서 실행할 때 index ownership, update atomicity, snapshot과 partial result를 설계합니다. 분산 query를 “모든 shard에 요청하고 합치기”로만 처리하지 않습니다.

## Primary-key routing의 한계

hash 또는 range partition key를 알면 한 shard로 routing할 수 있습니다. 다음 query는 다른 경로가 필요합니다.

- email로 user 찾기
- 상태별 order 목록
- 여러 shard의 시간 범위 scan
- global unique constraint
- aggregate와 top-K

선택:

- global secondary index
- local secondary index + scatter/gather
- 별도 query projection
- search system
- data model 변경

## Global secondary index

index key를 별도 shard space에 저장합니다.

```text
primary: user_id -> user record
index: email -> user_id
```

update는 두 위치를 바꿉니다.

```text
old email index 제거
new email index 추가
primary record 변경
```

같은 transaction으로 묶지 않으면 중간 불일치가 생깁니다. 허용 선택:

- cross-shard transaction으로 atomic update
- primary commit 뒤 asynchronous index update
- dual write + repair
- immutable event와 projection rebuild

각 선택에서 query가 어떤 stale·duplicate·missing 결과를 허용하는지 명시합니다.

## Local secondary index

각 data shard가 자신의 record에 대한 index를 유지합니다. update atomicity는 shard local transaction으로 해결하기 쉽지만 global query는 여러 shard를 조회해야 합니다.

```text
query status=OPEN
→ 모든 relevant shard에 local index scan
→ 결과 merge
```

shard 수가 늘면 fanout, tail latency와 partial failure가 커집니다.

## Scatter/gather

coordinator가 여러 shard에 같은 query를 보냅니다.

상태:

```text
QueryExecution {
  query_id
  routing_epoch
  snapshot_or_read_time
  target_shards
  completed_shards
  failed_shards
  partial_results
  deadline
}
```

응답 정책:

- 모든 shard 성공만 완전 결과
- partial result와 누락 shard 명시
- stale snapshot 허용
- retry 가능한 continuation token
- deadline 뒤 취소와 background 작업 정리

빈 result와 shard 실패를 혼동하지 않습니다.

## Snapshot consistency

각 shard를 서로 다른 시점에 읽으면 global invariant가 맞지 않는 결과가 생길 수 있습니다.

선택:

- global read timestamp 또는 transaction snapshot
- coordinator가 snapshot barrier를 생성
- 각 shard의 applied index token 사용
- eventual query임을 명시하고 snapshot consistency를 포기

snapshot timestamp를 사용하려면 각 shard가 그 timestamp의 version을 보존하고 읽을 수 있어야 합니다.

## Pagination과 rebalancing

continuation token에 단순 offset만 넣으면 shard split·move와 concurrent update에서 중복·누락이 생깁니다.

포함할 수 있는 정보:

```text
query shape hash
routing epoch
snapshot ID 또는 read time
shard별 cursor
last sort key와 tie-breaker
```

metadata epoch가 바뀌었을 때:

- old snapshot routing으로 계속 읽기
- token을 새 routing에 변환
- 명시적으로 token 만료

정책을 문서화합니다.

## Global uniqueness

`email`이 global unique라면 모든 shard가 local unique constraint만 가진 것으로는 부족합니다.

선택:

- email을 partition key로 한 authoritative index shard
- consensus 기반 name allocation service
- cross-shard transaction
- reservation token과 commit protocol

중복 감지 후 보상만으로 이미 외부에 노출된 identity 충돌이 허용되는지 제품 계약을 확인합니다.

## Top-K와 aggregation

각 shard에서 local top-K를 받아 merge할 수 있지만 comparator와 tie-breaker가 deterministic해야 합니다. 정확한 global result를 위해 shard별로 K보다 많은 후보가 필요할 수 있는 query도 있습니다.

aggregation에서 구분:

- associative·commutative merge 가능한 aggregate
- distinct, percentile처럼 추가 sketch·state가 필요한 aggregate
- exact result와 approximate result
- shard retry 중 duplicate partial result

partial result에 shard ID와 attempt ID를 붙여 deduplication합니다.

## Index repair

asynchronous index는 drift를 예상해야 합니다.

- primary record에서 index 재구축
- index entry가 가리키는 primary 존재·version 확인
- missing·extra·wrong target 분류
- shard epoch와 rebuild snapshot 기록
- live update와 rebuild delta 결합

repair가 old snapshot 결과로 새 index update를 덮지 않도록 version fence를 사용합니다.

## 실패 조건

- global index update를 primary update와 별개로 수행하면서 inconsistency를 숨깁니다.
- scatter/gather에서 빈 응답과 timeout을 같은 빈 목록으로 처리합니다.
- 서로 다른 shard 시점의 결과를 하나의 snapshot이라고 부릅니다.
- pagination token에 routing epoch와 snapshot이 없습니다.
- global unique constraint를 shard local constraint만으로 구현합니다.
- aggregation retry에서 같은 partial result를 두 번 더합니다.
- index rebuild가 live update보다 오래된 state를 덮어씁니다.

## 검증

다음 history를 만듭니다.

```text
1. user의 email을 A에서 B로 변경합니다.
2. primary commit 뒤 index update 전에 query합니다.
3. index update를 중복 전달합니다.
4. shard split 중 pagination을 이어갑니다.
5. 한 shard가 timeout합니다.
6. index rebuild와 새 update를 경쟁시킵니다.
```

각 API가 반환할 수 있는 결과, 오류와 metadata를 적고 automatic checker가 누락·중복·stale contract를 확인하도록 합니다.

## 완료 조건

- global index와 local index의 update·query 비용을 구분합니다.
- cross-shard query의 partial failure를 결과 metadata에 표현합니다.
- snapshot, routing epoch와 pagination token을 연결합니다.
- global uniqueness에 authoritative allocation 경계를 둡니다.
- asynchronous index의 repair와 live update fencing을 설계합니다.
