# 네트워크 권위, replication과 latency

## 문제

멀티플레이 게임은 local game을 network에 연결한 것이 아닙니다. 여러 machine이 서로 다른 시간과 불완전한 정보를 가진 채 하나의 game result에 동의해야 하는 시스템입니다.

```text
client input
→ local prediction 또는 pending view
→ transport
→ authoritative validation/simulation
→ replicated state/event
→ client reconciliation
→ presentation smoothing
```

transport가 packet을 전달해도 game rule이 안전해지는 것은 아닙니다. 반대로 모든 state를 reliable하게 보내면 latency와 head-of-line blocking이 사용자 경험을 망칠 수 있습니다. 먼저 **누가 무엇을 확정할 권한이 있는지** 정한 뒤 delivery와 presentation을 설계합니다.

## 핵심 상태

### authority 종류

- server authoritative: server가 rule result와 canonical state를 확정
- owner authoritative subset: 특정 low-risk state를 owning client가 제안/확정
- deterministic lockstep: 모든 peer가 같은 command와 simulation으로 결과 계산
- relay/host authoritative: host가 server 역할을 하지만 trust·fairness trade-off 존재
- backend authoritative: inventory, entitlement, economy, ranking처럼 match 밖 durable state

한 프로젝트 안에서도 subsystem마다 다를 수 있습니다.

### client가 보내는 것

좋은 기본값은 결과가 아니라 의도입니다.

```text
move direction
fire pressed with aim context
use item id
interact target candidate
ready/unready
```

`set_position`, `grant_reward`, `hit_enemy`를 그대로 받아들이지 않습니다. server는 current state, cooldown, ownership, visibility와 sequence를 검증합니다.

### replicated state와 event

- state snapshot: 현재 값, late join/recovery에 유용
- delta: 이전 acknowledged baseline과 차이
- reliable event: 반드시 한 번 이상 전달해야 하는 semantic event
- unreliable transient: 자주 갱신되고 최신 값이 더 중요한 state
- command acknowledgement: prediction history를 정리할 기준
- tombstone/despawn: object가 더 이상 유효하지 않음

“reliable”은 exactly once gameplay side effect를 뜻하지 않습니다. duplicate와 reconnect를 고려한 idempotency가 필요합니다.

### network time

- client local input time
- client simulation tick
- server receive/authoritative tick
- snapshot sequence
- estimated server time
- round-trip time와 jitter

clock synchronization은 완벽하지 않으므로 어느 허용 window에서 과거 state를 조회하거나 command를 거부할지 정합니다.

## 설계 계약

### authority table을 만듭니다

| state/action | proposer | validator | canonical owner | client view | correction |
|---|---|---|---|---|---|
| movement input | owning client | server | server pose | predicted | rewind/replay or snap |
| cosmetic emote | client | policy/server | replicated event | immediate | cancel if rejected |
| reward grant | match result/backend | backend | ledger | pending UI | reconcile transaction |
| camera | local client | none | local | local | none |

### prediction history를 bounded하게 보관합니다

- command sequence/tick
- predicted state before/after
- acknowledged server state
- deterministic replay input
- maximum history window

server correction을 받으면 acknowledged command까지 제거하고 남은 command를 다시 적용하거나, 게임 특성에 맞는 smoothing/snap 정책을 사용합니다.

### lag compensation의 trust boundary를 명시합니다

과거 target state를 조회해 hit를 검증할 수 있지만 client timestamp를 무제한 신뢰하지 않습니다.

- maximum rewind window
- server-observed latency bounds
- clock anomaly
- impossible aim/movement
- world/content version
- target history availability

lag compensation은 모든 player에게 같은 fairness를 보장하지 않으므로 design decision과 telemetry가 필요합니다.

### interest management를 state ownership과 연결합니다

모든 client에 모든 entity를 보내지 않습니다.

- spatial relevance
- team/party relevance
- ownership
- visibility/permission
- bandwidth priority
- dormancy/update frequency

보이지 않는다고 존재하지 않는 것은 아닙니다. gameplay query와 replication visibility를 분리합니다.

### reconnect와 late join을 설계합니다

현재 snapshot만으로 충분한 state, event history가 필요한 state, 재생성 가능한 state를 구분합니다. join 중 content version과 protocol compatibility를 확인합니다.

### network fault를 정상 입력으로 다룹니다

- latency와 jitter
- loss와 duplication
- reordering
- disconnect/reconnect
- server migration/restart
- partial backend failure

match simulation과 durable progression의 실패를 분리합니다.

## 대표 실패

### client가 hit와 reward 결과를 제출합니다

server가 plausible 여부만 대충 확인하면 forged result가 들어옵니다. client intent와 server-side rule query를 사용합니다.

### 모든 RPC를 reliable로 만듭니다

낡은 movement/event가 queue를 막아 최신 state가 늦어집니다. semantic 중요도와 최신성에 따라 channel을 선택합니다.

### snapshot arrival 순서대로 적용합니다

reordering된 old snapshot이 최신 state를 덮습니다. sequence/epoch와 baseline을 검증합니다.

### correction이 presentation event를 중복 생성합니다

prediction replay 중 sound, VFX, damage indicator가 다시 발생합니다. simulation event와 one-shot presentation dedupe를 분리합니다.

### network id를 session 밖 stable id로 저장합니다

reconnect/session restart에서 id가 재사용됩니다. profile/save identity와 network identity를 분리합니다.

### latency를 평균 하나로 표현합니다

jitter, tail, burst loss와 server frame spike가 사용자 experience를 결정합니다. 분포와 simulation tick delay를 함께 봅니다.

## 관찰과 검증

### command와 snapshot trace

```json
{
  "client": "c1",
  "command_sequence": 1881,
  "client_tick": 921,
  "server_receive_tick": 927,
  "server_decision": "accepted",
  "snapshot_sequence": 440,
  "acked_command": 1881,
  "position_error_cm": 14.2,
  "correction": "rewind_replay"
}
```

### fault matrix

| condition | expected behavior |
|---|---|
| 100ms latency | input remains responsive through prediction or accepted design delay |
| 5% loss | state converges; transient presentation may drop |
| reordering | older sequence ignored |
| duplicate command | no duplicate side effect |
| disconnect | local state enters explicit reconnect/abandoned state |
| reconnect | snapshot + acknowledgement rebuilds bounded history |
| incompatible content | join blocked with actionable reason |

### security와 correctness 검사

- impossible move/action을 server가 거부합니다.
- rejected command가 authoritative state를 바꾸지 않습니다.
- duplicate reliable delivery가 reward·damage를 중복 적용하지 않습니다.
- non-owner가 owner-only action을 호출하지 못합니다.
- hidden state가 unauthorized client에 replication되지 않습니다.
- replay/telemetry에서 first divergence와 correction spike를 찾습니다.

## 실습 연결

[authority와 latency 실습](../exercises/06-authority-and-latency/README.md)에서 command/snapshot trace를 분석하고 authority table, correction과 fault policy를 작성합니다.

## 기존 브랜치와 경계

- TCP·UDP·QUIC·loss·NAT의 원리는 `computer-networks`가 소유합니다.
- account·inventory·economy의 분산 수렴은 `distributed-services`가 소유합니다.
- 보안 위협 분석은 `cybersecurity`가 소유합니다.
- 현재 문서는 match gameplay authority, replication semantics, prediction·reconciliation과 latency UX를 소유합니다.

## 완료 기준

- subsystem별 authority와 client intent를 표로 작성합니다.
- state snapshot, delta, reliable event와 transient update를 구분합니다.
- prediction history, acknowledgement, correction과 presentation dedupe를 설계합니다.
- latency·jitter·loss·reordering·reconnect에서 correctness와 player experience를 검증합니다.
