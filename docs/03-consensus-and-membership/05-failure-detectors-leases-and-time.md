# Failure detector, lease와 시간 가정

## 목표

heartbeat와 timeout이 제공하는 것은 확정 사실이 아니라 failure suspicion임을 이해합니다. lease와 time-based optimization을 사용할 때 clock drift, network delay, pause와 fencing 조건을 safety contract에 포함합니다.

## Failure detector의 역할

완전 비동기 시스템에서 유한한 관찰만으로 느린 process와 crash한 process를 구분할 수 없습니다. failure detector는 실제 failure의 oracle이 아니라 **의심 결과를 제공하는 abstraction**입니다.

질문:

- crash한 process를 결국 의심합니까?
- 정상 process를 잘못 의심할 수 있습니까?
- 잘못된 의심이 결국 해제됩니까?
- 어떤 안정 기간과 message bound가 필요합니까?

consensus implementation은 잘못된 의심이 생겨도 safety를 유지하고, detector가 충분히 정확해지는 기간에 liveness를 얻도록 설계합니다.

## Heartbeat

heartbeat는 다음 evidence를 제공합니다.

```text
특정 시각 이후 peer가 보낸 protocol message를 관찰했습니다.
```

제공하지 않는 것:

- peer가 현재 살아 있다는 영구 보장
- peer가 disk에 필요한 state를 저장했다는 보장
- peer가 client request를 처리할 수 있다는 보장
- peer가 leader 권한을 유지한다는 보장

heartbeat payload에 term, commit index, applied index와 health generation을 포함하면 더 구체적인 상태를 관찰할 수 있지만 각각의 의미를 분리해야 합니다.

## Adaptive timeout

고정 timeout은 지연 분포와 pause에 맞지 않을 수 있습니다. RTT 관측으로 timeout을 조정할 수 있지만 다음을 주의합니다.

- 최근 정상 분포가 partition의 상한을 알려주지 않습니다.
- timeout이 길면 failover latency가 증가합니다.
- 너무 짧으면 false suspicion과 election churn이 증가합니다.
- coordinated pause가 모든 node의 timer와 heartbeat를 동시에 지연할 수 있습니다.

adaptive timeout은 liveness와 운영 안정성 최적화이지 safety mechanism이 아닙니다.

## Lease

lease는 정해진 기간 동안 holder가 resource를 사용할 권한을 갖는 계약입니다.

```text
lease_id
holder
start 또는 grant evidence
expiry
fencing_token
```

분산 lease가 안전하려면 누가 시간과 expiry를 판단하는지, clock error bound가 무엇인지, lease renewal과 overlap을 어떻게 막는지 정해야 합니다.

### Server-authoritative lease

하나의 authoritative store가 자신의 시간으로 grant·expiry를 판단하고 client는 lease ID와 fencing token을 사용합니다. client local clock은 remaining time을 낙관적으로 판단하는 데 사용하지 않습니다.

### Quorum lease

quorum이 일정 기간 다른 leader를 지지하지 않겠다는 조건을 사용합니다. message delay와 clock drift bound가 필요하며 구현 proof와 일치해야 합니다.

## Fencing token

lease만으로 오래된 holder의 작업이 사라지는 것은 아닙니다.

```text
holder A가 lease 41을 얻습니다.
A가 오래 pause됩니다.
lease가 만료되고 B가 lease 42를 얻습니다.
A가 깨어나 external storage에 write합니다.
```

external resource가 monotonic token을 확인해야 합니다.

```text
write(token=41) -> reject, last_seen=42
write(token=42) -> accept
```

fencing은 old holder와 new holder가 잠시 동시에 실행돼도 external effect를 하나의 epoch로 제한합니다.

## Lease read와 ReadIndex

leader가 linearizable read를 제공하는 방법을 비교합니다.

### ReadIndex 또는 quorum confirmation

- 현재 term의 leadership을 majority와 확인합니다.
- 안전성에 physical clock bound가 덜 필요합니다.
- read마다 quorum round-trip 또는 batching 비용이 있습니다.

### Lease read

- 유효한 lease 동안 local read가 가능합니다.
- clock drift, pause, message delay와 renewal protocol이 safety assumption에 들어갑니다.
- old leader가 lease를 과대평가하지 않도록 보수적인 expiry 계산이 필요합니다.

선택은 latency 요구와 시간 인프라의 신뢰도에 따라 달라집니다.

## Clock jump와 process pause

다음 event를 model에 포함합니다.

- wall clock이 앞으로 또는 뒤로 step
- monotonic clock은 진행하지만 process가 suspend
- GC 또는 VM pause
- host migration
- NTP slew
- timer callback 지연

lease duration 측정에는 보통 monotonic clock을 사용하지만, process pause 중 lease가 실제로 만료될 수 있습니다. 깨어난 holder는 external write 전에 token을 다시 검증해야 합니다.

## Leadership transfer와 lease

leader transfer를 수행할 때 기존 leader는 새 write 승인을 멈추고 target의 log progress를 확인한 뒤 transfer message를 보냅니다. lease가 있다면 old lease expiry와 new leader activation이 겹치지 않거나 fencing token이 겹침을 막아야 합니다.

## Failure detector 관측 지표

- heartbeat RTT와 loss
- election timeout 분포
- false election 또는 term churn
- leader tenure
- quorum contact age
- lease remaining uncertainty
- clock offset·drift bound
- process pause duration
- fencing rejection 수

평균값보다 tail과 failure period의 분포를 봅니다.

## 실패 조건

- timeout을 crash의 확정 판정으로 기록합니다.
- adaptive timeout으로 safety가 향상됐다고 주장합니다.
- client local clock만으로 lease validity를 판단합니다.
- lease holder가 external resource에 fencing token 없이 write합니다.
- monotonic clock이면 process pause 문제가 없다고 봅니다.
- lease read를 사용하면서 clock drift와 renewal proof를 문서화하지 않습니다.
- leader transfer와 old lease overlap을 검증하지 않습니다.

## 검증

결정적 simulation에 다음 event를 추가합니다.

```text
pause(node, duration)
delay_link(A, B, duration)
jump_wall_clock(node, delta)
advance_monotonic(node, delta)
expire_lease(resource)
reject_stale_token(resource, token)
```

검사할 schedule:

1. leader A가 lease와 token 10을 얻습니다.
2. A를 lease 기간보다 오래 pause합니다.
3. B가 token 11로 leader가 됩니다.
4. A가 깨어나 write를 시도합니다.
5. external resource가 token 10을 거절합니다.

## 완료 조건

- heartbeat와 failure fact를 구분합니다.
- timeout을 liveness 도구로 사용하고 safety를 quorum·term에 둡니다.
- lease의 clock·pause·renewal 가정을 명시합니다.
- external effect에 monotonic fencing token을 적용합니다.
- lease read와 quorum-confirmed read의 trade-off를 설명합니다.
