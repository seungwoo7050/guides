# Anti-entropy, conflict와 eventual convergence

## 목표

replica가 일시적으로 다른 state를 가질 수 있는 시스템에서 차이를 찾고, version을 교환하고, conflict를 보존·병합해 결국 수렴시키는 경로를 설계합니다. “나중에 맞아집니다”를 repair protocol과 종료 조건으로 구체화합니다.

## 왜 background repair가 필요합니까?

foreground write가 성공해도 모든 replica가 update를 받았다는 뜻은 아닐 수 있습니다.

```text
write는 W개 replica에서 성공합니다.
나머지 replica는 timeout 또는 partition으로 이전 값을 유지합니다.
client traffic이 그 key를 다시 읽지 않을 수 있습니다.
```

read repair만 사용하면 읽히지 않는 key는 영원히 오래된 상태로 남을 수 있습니다. anti-entropy는 client request와 독립적으로 replica state를 비교하고 복구합니다.

## Anti-entropy 단계

```text
1. 비교할 replica와 key range를 선택합니다.
2. range summary 또는 version digest를 교환합니다.
3. 다른 구간을 더 작게 좁힙니다.
4. 필요한 object와 causal metadata를 전송합니다.
5. merge 또는 dominant version 선택을 적용합니다.
6. convergence와 pending difference를 기록합니다.
```

전체 data를 매번 전송하지 않기 위해 다음을 사용할 수 있습니다.

- Merkle tree 또는 hash tree
- range checksum
- per-partition generation
- log position·change stream
- version summary

hash가 같다는 것은 해당 summary 범위와 알고리즘 아래 bytes가 같다는 근거입니다. application-level invariant가 맞다는 증거는 아닙니다.

## Read repair

read quorum에서 오래된 replica를 발견하면 response 전 또는 후 update할 수 있습니다.

### Blocking repair

repair가 끝난 뒤 response합니다.

- 같은 read가 확인한 replica의 freshness는 높아집니다.
- latency가 증가합니다.
- read가 모든 divergent replica를 본 것은 아닐 수 있습니다.

### Asynchronous repair

최신 값을 반환하고 background task로 repair합니다.

- read latency를 줄일 수 있습니다.
- task 유실과 반복 실패를 추적해야 합니다.
- 다음 read가 같은 stale replica를 볼 수 있습니다.

read repair는 anti-entropy의 대체물이 아니라 foreground 보완 경로입니다.

## Conflict 표현

conflict를 감지했을 때 한 값을 즉시 버리지 않습니다.

```text
siblings = {
  v2A: shipping_address = Seoul,
  v2B: shipping_address = Busan
}
```

가능한 merge:

- client에게 siblings와 context 반환
- application-specific field merge
- set·counter 같은 convergent data type
- manual resolution workflow
- deterministic winner 선택

merge 함수가 replica마다 같은 결과를 내려면 최소한 다음을 검토합니다.

- commutative: 순서가 달라도 같은 결과
- associative: 묶는 방식이 달라도 같은 결과
- idempotent: 같은 update를 여러 번 적용해도 같은 결과

모든 업무 객체를 자동 merge할 수는 없습니다. 예약 가능한 좌석, 잔액과 unique username은 conflict-free merge보다 coordination이 필요할 수 있습니다.

## CRDT의 위치

CRDT는 특정 state 또는 operation merge가 replica 순서와 중복에 안전하도록 설계된 data type입니다.

사용 전 질문:

- state-based인가 operation-based인가?
- causal delivery 또는 exactly-once에 가까운 추가 가정이 필요한가?
- tombstone·metadata가 얼마나 증가하는가?
- concurrent add와 remove 의미가 업무 요구와 맞는가?
- replica membership과 garbage collection을 어떻게 처리하는가?

“CRDT를 사용하므로 consistency 문제 없음”은 부정확합니다. 데이터 타입의 merge 의미가 제품 의미와 일치해야 합니다.

## Repair ownership

background repair에는 명시적인 소유자가 필요합니다.

```text
RepairTask {
  range
  source_replica
  target_replica
  expected_epoch
  cursor
  attempt
  last_error
  next_attempt_at
}
```

운영 계약:

- 최대 동시 실행과 bandwidth
- foreground traffic과의 우선순위
- retry·backoff·deadline
- epoch 변경 시 취소 또는 재시작
- checksum mismatch와 corruption의 구분
- 완료한 range와 아직 남은 range

repair가 무한 retry하며 foreground latency를 망치지 않도록 load control이 필요합니다. 일반적인 역압 원리는 `distributed-services`와 `web-infra`에 연결하되, 여기서는 replica convergence 상태를 소유합니다.

## Tombstone과 compaction

anti-entropy가 delete를 전달하려면 tombstone을 충분히 오래 보존해야 합니다.

GC를 위한 evidence 예:

- 모든 active replica의 version frontier가 tombstone을 지났습니다.
- 제거된 replica는 configuration에서 fenced됐습니다.
- backup restore point가 tombstone 이전이면 별도 migration이 있습니다.
- 최대 offline 기간이 지났으며 오래된 replica는 full bootstrap만 허용합니다.

시간만 지나면 삭제하는 정책은 delayed replica와 clock skew를 고려해야 합니다.

## Divergence와 corruption을 구분합니다

정상적인 version 차이와 storage corruption은 처리 방식이 다릅니다.

- 정상 divergence: version 관계와 merge 규칙으로 해결
- missing data: authoritative replica에서 복구
- checksum mismatch: disk·memory·software corruption 조사
- impossible version: metadata corruption 또는 protocol bug

corruption을 최신 version으로 잘못 판단해 다른 replica에 전파하지 않도록 provenance와 checksum을 기록합니다.

## Convergence 측정

“결국 수렴”을 운영 가능한 값으로 바꿉니다.

- divergent key 또는 range 수
- oldest unrepaired version age
- repair queue depth
- bytes scanned·transferred
- conflict sibling 수
- tombstone age와 GC candidate
- replica frontier 차이
- full bootstrap 진행률

수렴 완료 조건은 단순히 queue가 비었다는 것이 아니라 target replica state가 expected epoch와 version frontier를 만족한다는 것입니다.

## 실패 조건

- read repair만으로 모든 key가 수렴한다고 가정합니다.
- conflict를 발견하자마자 local timestamp가 큰 값을 선택합니다.
- merge 함수의 commutativity·associativity·idempotence를 검토하지 않습니다.
- CRDT를 제품 의미 검토 없이 도입합니다.
- membership epoch가 바뀐 동안 오래된 repair task가 write합니다.
- tombstone을 시간만 보고 제거합니다.
- checksum mismatch를 정상 stale replica로 처리합니다.
- repair queue가 비었다는 사실만으로 convergence를 선언합니다.

## 검증

다음 schedule을 결정적으로 재현합니다.

```text
1. replica C를 partition합니다.
2. A와 B에서 write v2를 성공시킵니다.
3. C에서 concurrent write v2C를 허용합니다.
4. partition을 해제합니다.
5. anti-entropy 순서를 A-C, B-C, A-B로 바꿔 실행합니다.
6. 모든 순서에서 같은 sibling set 또는 merge result로 수렴하는지 봅니다.
```

추가 검사:

- 같은 repair message를 중복 전달합니다.
- delete tombstone 전에 오래된 replica를 복구합니다.
- repair 중 membership epoch를 변경합니다.
- object bytes를 손상시켜 checksum mismatch를 만듭니다.

## 완료 조건

- read repair와 anti-entropy의 역할을 구분합니다.
- conflict를 version relation과 merge policy로 명시합니다.
- convergent merge가 필요한 대수적 성질을 설명합니다.
- tombstone GC를 replica frontier와 membership evidence에 연결합니다.
- divergence, missing data와 corruption을 서로 다른 상태로 다룹니다.
- convergence를 queue가 아닌 replica state 지표로 판정합니다.
