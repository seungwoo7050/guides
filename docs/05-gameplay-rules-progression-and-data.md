# 게임 규칙, 진행 상태와 data-driven 설계

## 문제

게임 규칙은 코드에 흩어진 `if` 문이나 animation event의 집합이 아닙니다. 플레이어 행동을 허용·거부하고 score, inventory, objective, progression과 reward를 바꾸는 **상태 전이 계약**입니다.

규칙의 owner가 불분명하면 다음 문제가 생깁니다.

- animation이 끝났다는 이유로 damage가 적용됩니다.
- UI가 reward 수량을 계산합니다.
- client와 server가 서로 다른 rule table을 사용합니다.
- designer data 변경이 save와 replay compatibility를 깨뜨립니다.
- live event 종료 뒤 이미 진행 중인 match의 규칙이 중간에 바뀝니다.
- analytics event가 실제 transaction 성공보다 먼저 기록됩니다.

## 핵심 상태

### 규칙의 입력과 결과

```text
Command
+ current authoritative state
+ immutable rule/config version
+ deterministic context
→ Accepted(next state, domain events)
  or Rejected(reason, unchanged state)
```

거부는 예외적인 bug가 아니라 정상 결과입니다. cooldown, resource 부족, phase 불일치, stale sequence와 권한 부족을 구분합니다.

### 상태 범위

| 범위 | 예 | 대표 owner |
|---|---|---|
| entity | health, status, cooldown | gameplay component/system |
| player-in-match | loadout, score, respawn | match player state |
| global match | phase, timer, objectives | match rule state |
| persistent profile | unlock, settings, progression | profile/save/backend |
| economy ledger | currency, purchase, reward grant | authoritative service/ledger |
| presentation | combo text, hit marker | UI/VFX/audio |

match state와 persistent profile transaction을 하나의 object로 합치지 않습니다.

### state machine과 phase

명시적 phase는 허용되는 command와 timer를 제한합니다.

```text
Preparing
→ Countdown
→ Active
→ Overtime
→ Resolving
→ ResultsCommitted
→ Closed
```

phase transition은 event 이름뿐 아니라 precondition, side effect, idempotency와 rollback 가능 여부를 가집니다.

### authored data와 runtime state

- rule definition: damage formula, item definition, spawn table
- runtime instance: 현재 HP, stack count, next spawn tick
- content version: 어떤 definition set으로 만들어졌는지
- migration policy: definition이 바뀌었을 때 기존 instance를 어떻게 해석하는지

asset 이름을 영구 item id로 사용하지 않습니다.

## 설계 계약

### rule과 presentation을 분리합니다

```text
AttackCommand
→ combat rule validates
→ DamageApplied event
→ health state updates
→ animation/VFX/audio/HUD consume event
```

animation event는 hit window를 요청하거나 authored marker를 제공할 수 있지만 최종 damage와 ownership은 rule layer에 둡니다. 프로젝트에 따라 animation-driven gameplay를 사용할 수 있으나, replay·network·test에서 동일한 marker semantics를 보장해야 합니다.

### transaction boundary를 정합니다

reward 예시:

```text
match result confirmed
→ reward intent with idempotency key
→ persistent transaction
→ commit result
→ profile view update
→ telemetry
```

UI 표시나 network response가 commit보다 먼저 정본을 바꾸지 않습니다.

### data-driven은 validation을 포함합니다

코드를 data로 옮기는 것만으로 안전해지지 않습니다. schema와 validator를 둡니다.

- stable id uniqueness
- reference existence
- range와 unit
- cycle detection
- phase compatibility
- memory/load classification
- localization key
- deprecated field
- content version와 minimum runtime version

### config snapshot을 사용합니다

진행 중인 match가 live config를 매 tick 읽으면 동일 match 안에서 규칙이 바뀔 수 있습니다. match start에서 rule/config version을 snapshot하고 결과·replay·telemetry에 기록합니다.

### 불변식을 먼저 씁니다

예:

- currency balance는 commit된 ledger entry의 합과 일치합니다.
- dead entity는 gameplay command를 accept하지 않습니다.
- item stack은 definition의 max stack을 넘지 않습니다.
- match result는 한 번만 commit됩니다.
- 동일 reward idempotency key는 중복 grant하지 않습니다.

## 대표 실패

### gameplay tag나 string이 무제한 global protocol이 됩니다

편리한 문자열 event가 producer·consumer 계약과 version을 숨깁니다. public event에는 schema, owner와 lifecycle을 둡니다.

### derived value를 저장하고 둘 다 수정합니다

level과 experience, total score와 round score처럼 다시 계산 가능한 값을 함께 정본으로 유지하면 drift가 생깁니다. 하나를 정본으로 정하고 migration cost를 고려합니다.

### designer data가 executable code처럼 동작하지만 review가 없습니다

formula, condition graph와 script가 rule을 바꾼다면 code와 같은 validation, diff, test와 release gate가 필요합니다.

### result event를 retry하면서 side effect를 중복 수행합니다

reward, achievement와 analytics를 하나의 callback에 넣으면 retry 시 중복됩니다. idempotency와 각각의 delivery contract를 둡니다.

### telemetry가 rule decision을 대신합니다

event가 찍혔다는 사실은 transaction commit을 증명하지 않습니다. authoritative state와 event source를 연결합니다.

## 관찰과 검증

### decision trace

```json
{
  "tick": 880,
  "match": "m-12",
  "actor": "player-3",
  "command": "use_item",
  "item_id": "healing-small",
  "rule_version": "arena-rules@17",
  "decision": "rejected",
  "reason": "cooldown_active",
  "state_hash_before": "...",
  "state_hash_after": "..."
}
```

거부일 때 보호 상태가 바뀌지 않았는지 확인합니다.

### property와 scenario 검사

- accepted transition은 invariant를 유지합니다.
- rejected transition은 state를 바꾸지 않습니다.
- command order를 바꾸면 달라져야 하는 것과 같아야 하는 것을 구분합니다.
- content validator가 broken reference와 invalid range를 거부합니다.
- rule version이 다른 replay를 명시적으로 거부하거나 migration합니다.
- reward retry와 reconnect에서 중복 commit이 없습니다.

### balance와 correctness를 구분합니다

“재미있는가”, “적절한 damage인가”는 design/balance 판단입니다. “정의한 formula와 invariant를 따르는가”는 correctness입니다. 자동 테스트는 후자를 보장하고 playtest는 전자의 근거를 제공합니다.

## 실습 연결

Capstone의 `gameplay-rules.md`와 `state-ownership.csv`에서 match phase, command, rejection과 persistent reward 경계를 정의합니다. [release readiness 실습](../exercises/08-release-readiness/README.md)에서는 content version과 save compatibility를 검토합니다.

## 기존 브랜치와 경계

- 일반 transaction과 DB constraint는 `database-systems`가 소유합니다.
- 서비스 간 reward·inventory 수렴은 `distributed-services`가 소유합니다.
- 현재 문서는 match rule, phase, authored definition과 presentation 경계를 소유합니다.

## 완료 기준

- command와 rule result를 accepted/rejected transition으로 표현합니다.
- match, entity, profile, economy와 presentation state의 owner를 분리합니다.
- authored data에 schema·version·validator·snapshot 정책을 둡니다.
- retry·reconnect·content 변경에서도 불변식과 idempotency를 검증합니다.
