# Quorum, version과 읽기·쓰기 경로

## 목표

replica 수와 quorum 교차를 실제 read·write protocol로 연결합니다. `R + W > N` 같은 수식이 어떤 전제 아래 유용한지, 그리고 version·concurrent write·failure·sloppy quorum 때문에 어떤 책임이 남는지 이해합니다.

## 기본 quorum

`N`개 replica 중 write가 `W`개 acknowledgment를 받고, read가 `R`개 replica를 조회한다고 가정합니다.

```text
R + W > N
```

이면 모든 read quorum과 write quorum이 적어도 한 replica에서 교차합니다.

또한 두 write quorum이 교차하려면 다음을 사용할 수 있습니다.

```text
2W > N
```

하지만 교차 자체는 최신 값을 자동 선택하지 않습니다. 교차 replica가 여러 version을 가질 수 있고, concurrent write의 순서를 결정할 metadata와 protocol이 필요합니다.

## Versioned value

replica는 값만 저장하지 않고 version을 함께 저장합니다.

```text
VersionedValue {
  key
  value 또는 tombstone
  version
  causal context
  writer epoch
}
```

version 선택지는 다음과 같습니다.

- consensus log index와 term
- monotonic primary epoch와 sequence
- vector 또는 dotted version vector
- timestamp와 tie-breaker
- application-defined version

각 version은 어떤 순서 관계를 표현하는지 명시해야 합니다.

## Write path

leaderless quorum write의 예:

```text
1. coordinator가 현재 version context를 확인합니다.
2. 새 version을 생성합니다.
3. N replica에 write를 보냅니다.
4. W개 durable acknowledgment를 기다립니다.
5. client에 성공을 반환합니다.
```

설계 질문:

- W개 중 몇 개가 실제 durable flush를 완료했습니까?
- coordinator가 crash하면 retry가 같은 write인지 새 concurrent write인지 어떻게 압니까?
- replica가 오래된 version을 거절합니까, sibling으로 저장합니까?
- hinted handoff가 원래 replica의 quorum을 대체합니까?
- write timeout 뒤 일부 replica만 update된 상태를 누가 repair합니까?

## Read path

일반적인 quorum read:

```text
1. R개 replica에서 versioned value를 읽습니다.
2. version 관계를 비교합니다.
3. 하나가 다른 모든 version을 지배하면 선택합니다.
4. concurrent sibling이면 merge·모두 반환·거절 중 하나를 선택합니다.
5. 오래된 replica를 read repair합니다.
```

이 protocol도 linearizability를 자동 보장하지 않습니다.

- read와 concurrent write가 겹칠 수 있습니다.
- coordinator가 stale membership을 사용할 수 있습니다.
- version ordering이 real-time order를 보존하지 않을 수 있습니다.
- sloppy quorum은 실제 replica set 교차를 약화시킬 수 있습니다.
- read repair가 response 이후 비동기라면 다른 read가 stale할 수 있습니다.

strong consistency가 필요하면 ABD 계열 register, lease·leader read 또는 consensus 기반 protocol처럼 더 구체적인 알고리즘이 필요합니다.

## Concurrent write

두 client가 같은 base version에서 서로 다른 값을 쓰면 version이 concurrent할 수 있습니다.

```text
base v1
├── write A -> v2A
└── write B -> v2B
```

처리 선택:

- sibling을 둘 다 보존하고 client 또는 application이 merge
- data type별 deterministic merge
- last-write-wins
- compare-and-set로 한쪽을 거절
- consensus로 하나의 order 선택

last-write-wins는 간단하지만 clock skew나 tie-break 때문에 완료된 update가 사라질 수 있습니다. 허용 가능한 데이터에만 사용합니다.

## Tombstone과 delete

delete를 값 부재로만 표현하면 offline replica의 오래된 값이 anti-entropy에서 되살아날 수 있습니다.

따라서 tombstone도 versioned update로 저장합니다.

GC 조건:

- 모든 relevant replica가 tombstone 또는 그 이후 version을 봤다는 근거
- offline replica 복구의 최대 기간
- repair와 backup restore 경계
- membership에서 제거된 replica의 처리

GC가 너무 빠르면 resurrection, 너무 늦으면 저장 공간과 scan 비용이 증가합니다.

## Sloppy quorum과 hinted handoff

home replica가 unavailable할 때 다른 node에 임시로 저장해 availability를 높일 수 있습니다.

이때 `N`, `R`, `W`가 실제로 어떤 node 집합에 적용되는지 달라집니다.

- 서로 다른 coordinator가 겹치지 않는 임시 replica set을 선택할 수 있습니다.
- hinted value가 home replica로 이동하기 전 read에서 누락될 수 있습니다.
- temporary node failure가 추가 durability risk를 만듭니다.

sloppy quorum은 일반 quorum과 같은 보장을 자동으로 제공하지 않습니다.

## Membership과 topology

quorum 계산은 replica set version에 의존합니다.

```text
ReplicaSet(key, epoch=17) = {A, B, C}
```

stale coordinator가 epoch 16의 `{D, E, F}`에 write하면 교차 규칙이 깨질 수 있습니다. routing metadata에 epoch 또는 configuration version을 두고 old configuration write를 fencing합니다.

failure domain도 replica 선택에 포함합니다.

- host
- rack
- availability zone
- region
- power·network plane

`N=3`이 서로 다른 zone에 배치됐는지, 같은 rack에 몰렸는지에 따라 실제 fault tolerance가 다릅니다.

## Capacity와 latency

quorum을 늘리면 보장과 비용이 함께 달라집니다.

- `W` 증가: write latency·durability·write conflict 관찰 범위 변화
- `R` 증가: read latency·freshness·repair 기회 변화
- tail latency: 가장 빠른 R/W 응답을 기다려도 slow replica와 network 분포의 영향을 받음
- fanout: node당 요청 수와 background repair 부하 증가

성능 측정에서는 성공 quorum뿐 아니라 straggler, timeout, retry와 repair traffic을 포함합니다.

## 실패 조건

- `R + W > N`만 적고 version compare 규칙을 적지 않습니다.
- acknowledgment가 memory 수신인지 durable commit인지 구분하지 않습니다.
- write timeout의 partial state를 지웁니다.
- concurrent version을 timestamp 한 개로 덮어씁니다.
- delete를 즉시 물리 제거해 오래된 replica에서 값이 부활합니다.
- sloppy quorum을 strict quorum과 같은 것으로 설명합니다.
- replica set 변경에 epoch와 fencing이 없습니다.

## 검증

[quorum register 실습](../../exercises/02-replication-and-consistency/02-quorum-register/README.md)은 `N=5`에서 read·write·failure schedule을 제공합니다.

검사 항목:

- 실제 read와 write set이 교차합니까?
- 교차 node의 version이 최신임을 판정할 수 있습니까?
- concurrent sibling을 잃지 않습니까?
- timeout 뒤 retry가 update를 중복·덮어쓰지 않습니까?
- tombstone이 offline replica의 값을 막습니까?
- membership epoch가 다른 write를 거절합니까?

## 완료 조건

- quorum 교차와 consistency protocol을 구분합니다.
- version이 표현하는 순서와 concurrency를 명시합니다.
- read·write timeout 뒤 partial replica state를 다룹니다.
- tombstone과 GC의 resurrection 위험을 설명합니다.
- sloppy quorum과 membership change가 교차 보장에 미치는 영향을 검토합니다.
