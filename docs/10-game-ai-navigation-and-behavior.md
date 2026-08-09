# 게임 AI, navigation과 behavior 통합

## 문제

게임 AI는 머신러닝 모델과 동일하지 않습니다. 많은 게임에서 AI는 perception, world query, navigation, decision, action execution과 animation/presentation을 연결하는 runtime system입니다. 중요한 문제는 “어떤 알고리즘을 쓰는가”뿐 아니라 다음 계약입니다.

이 장은 `game-development`에 별도의 AI 소유 범위를 추가하지 않습니다. navigation·behavior를 **입력·엔티티 상태, 물리·이동·표현 하위 시스템, frame budget과 authoritative rule에 연결하는 게임 계층 통합 사례**로 사용합니다. graph search 자체는 `algorithms`, 모델 학습은 `machine-learning`의 정본을 따릅니다.

- AI가 보는 world state는 언제의 snapshot입니까?
- decision budget을 여러 agent 사이에 어떻게 나눕니까?
- path가 계산된 뒤 world가 바뀌면 어떻게 합니까?
- behavior가 command를 제출합니까, state를 직접 수정합니까?
- server authority와 client presentation에서 어떤 AI가 실행됩니까?
- debug trace로 왜 그 결정을 했는지 설명할 수 있습니까?

## 핵심 상태

### pipeline

```text
world/perception events
→ memory or blackboard
→ goal/decision selection
→ plan/path request
→ action command
→ gameplay validation
→ movement/animation execution
→ result feedback
```

각 단계는 async 또는 다른 frequency로 실행될 수 있습니다.

### world representation

- direct entity query
- spatial index
- navigation mesh/graph
- tactical points/cover data
- perception cache
- blackboard/memory
- authored behavior data

AI memory는 authoritative world와 다를 수 있습니다. stale 여부와 forget policy를 둡니다.

### navigation state

```text
Idle
→ RequestingPath
→ PathReady
→ Following
→ Blocked/Replanning
→ Arrived
→ Cancelled/Failed
```

path id, nav data version, agent settings와 target generation을 기록합니다.

### behavior 선택

- finite state machine
- behavior tree
- utility scoring
- goal-oriented planning
- scripted sequence
- hybrid

도구 선택보다 transition, interruption, priority와 side effect owner가 중요합니다.

## 설계 계약

### AI는 gameplay command를 제출합니다

AI가 health, inventory나 transform을 직접 수정하지 않고 player와 같은 rule interface 또는 명시적 privileged command를 사용합니다.

```text
AI decision: use ability X on target Y
→ command
→ authoritative rule validation
→ accepted/rejected event
→ behavior receives result
```

이 구조는 test, network와 replay를 단순화합니다.

### update budget을 명시합니다

모든 agent를 매 frame full decision하지 않습니다.

- perception frequency
- decision frequency
- path request quota
- maximum nodes/queries per frame
- distance/importance LOD
- server/client 실행 위치
- overload degradation

budget drop이 gameplay fairness를 깨지 않는지 검토합니다.

### async result에 version을 붙입니다

pathfinding, cover query와 expensive planning completion 때 agent, world, target이 바뀔 수 있습니다.

```text
request_id
agent generation
target generation
world/nav version
request tick
cancel token
```

현재 state와 맞지 않으면 result를 버립니다.

### interruption과 cleanup을 정의합니다

stun, death, target loss, world unload와 higher-priority goal에서 action을 중단할 때 movement, animation, reserved resource와 event subscription을 정리합니다.

### navigation과 movement owner를 분리합니다

navigation은 corridor/desired direction을 제공하고 movement system이 collision·acceleration·authority를 적용합니다. path point를 transform에 직접 대입하지 않습니다.

### 설명 가능한 debug trace를 둡니다

최소한 다음을 남깁니다.

- observed facts와 age
- considered goals/actions
- score/condition 결과
- selected action과 reason
- request/result id
- interruption/failure reason

## 대표 실패

### blackboard가 global mutable state가 됩니다

누가 field를 쓰는지 모르고 stale state가 남습니다. typed key, owner, lifetime과 update source를 정합니다.

### behavior tree node가 gameplay state를 직접 수정합니다

재시도·abort·network에서 side effect가 중복됩니다. action command와 idempotent result를 사용합니다.

### path completion이 despawn된 agent에 적용됩니다

weak/generation handle과 cancellation이 필요합니다.

### agent 수가 늘면 frame spike가 발생합니다

동일 frame에 perception·decision·path request가 몰립니다. scheduling과 quota를 둡니다.

### visual line-of-sight와 gameplay visibility가 다릅니다

renderer occlusion, camera frustum을 AI perception 정본으로 쓰지 않습니다. collision/query layer와 rule을 사용합니다.

### client AI가 competitive result를 확정합니다

bot, NPC와 projectile logic의 authority를 server 또는 agreed deterministic simulation에 둡니다.

## 관찰과 검증

### deterministic scenario

작은 world fixture에 다음을 고정합니다.

- entities와 stable ids
- obstacles/nav version
- initial memory
- command/result sequence
- decision budget
- random stream

예상 action sequence와 invariant를 검사합니다. exact path point보다 “forbidden area를 통과하지 않음”, “blocked 뒤 defined time 안에 replan” 같은 semantic property가 더 안정적일 수 있습니다.

### failure scenarios

- target despawn during path request
- navmesh update during follow
- stun/death during action
- path unavailable
- budget overload
- perception event reordering
- world unload
- network correction

### profile

- agent count별 perception/decision/path 비용
- longest query
- queued requests와 cancellation rate
- replans per agent
- invalid/stale result drop
- AI LOD별 quality와 CPU 절감

## 실습 연결

Capstone의 지원 문서 `ai-and-navigation.md`에서 두 종류 agent의 perception, goal, navigation, action command와 debug trace를 설계합니다. 이 산출물은 movement·presentation·authority·profiling 계약을 같은 agent lifecycle에 적용했는지 보여 주며, pathfinding 알고리즘 자체의 구현을 요구하지 않습니다.

## 기존 브랜치와 경계

- graph search와 pathfinding 알고리즘은 `algorithms`가 소유합니다.
- machine learning model은 `machine-learning`이 소유합니다.
- movement와 collision은 이 브랜치의 07장이 소유합니다.
- 현재 문서는 브랜치의 정본 `owns` 가운데 “물리·애니메이션·오디오·렌더링 하위 시스템의 게임 계층 통합”과 “frame budget·profiling·client/server authoritative 경계의 게임 맥락”을 agent 사례에 적용합니다.

## 완료 기준

아래 항목은 별도 AI 종료 능력이 아니라 게임 계층 통합 근거의 완료 기준입니다.

- perception→memory→decision→command→result pipeline을 상태와 owner로 설명합니다.
- agent 수와 중요도에 따른 update budget과 degradation을 설계합니다.
- async path/plan result에 generation·world version·cancel 계약을 둡니다.
- interruption, stale result와 overload를 deterministic fixture와 profile로 검증합니다.
- 위 결과를 AI 전문성의 별도 종료 주장으로 사용하지 않고, game loop·entity lifetime·movement·presentation·authority·frame budget 경계를 복원하고 검증한 근거로 연결합니다.
