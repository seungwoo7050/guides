# 월드, 장면, 엔티티와 컴포넌트 수명

## 문제

게임 객체는 생성자에서 만들어지고 destructor에서 끝나는 일반 객체보다 복잡한 수명을 가집니다. editor serialization, prefab/scene instantiation, network spawn, asynchronous asset load, streaming, pooling과 deferred destruction이 함께 작동합니다.

“object가 존재한다”는 표현은 최소 다음 중 어느 상태인지 구분해야 합니다.

```text
asset metadata로 발견됨
→ data가 load됨
→ runtime object가 생성됨
→ dependency가 연결됨
→ gameplay 사용 가능
→ visible/active
→ deactivating
→ destroy 요청됨
→ reference에서 제거됨
→ memory 해제 또는 pool 반환
```

수명을 명시하지 않으면 stale reference, initialization race, double registration, event leak와 unload 불가능한 asset graph가 발생합니다.

## 핵심 상태

### world와 scene

- **world**: simulation과 entity가 속한 최상위 runtime context
- **scene/level**: world의 일부를 저장·stream·편집하는 단위
- **subscene/chunk**: loading과 visibility를 위한 더 작은 단위
- **persistent subsystem**: world travel을 넘어 유지되는 시스템인지 명시

엔진에 따라 용어가 다르지만, map file과 runtime world를 같은 identity로 취급하지 않습니다.

### entity identity

| identity | 용도 | 재사용 정책 |
|---|---|---|
| runtime handle | 현재 process의 빠른 참조 | generation으로 stale 검출 |
| stable content id | authored object 또는 asset 식별 | rename/migration 규칙 필요 |
| save id | 저장된 상태와 runtime object 연결 | schema·spawn policy 필요 |
| network id | replicated object 연결 | session scope와 recycle 주의 |
| analytics id | event correlation | 개인정보·cardinality 제한 |

pointer나 array index만 장기 identity로 저장하지 않습니다.

### component와 subsystem

component는 data와 behavior를 조합하는 수단이지만 무조건 작은 class로 쪼개는 것이 목적은 아닙니다.

- entity/actor는 identity와 aggregate lifetime을 소유합니다.
- component는 특정 capability와 local state를 소유합니다.
- system/subsystem은 여러 entity를 질의하거나 global resource를 조정합니다.
- service adapter는 platform·network·storage 외부 경계를 소유합니다.

누가 update 순서와 cross-component invariant를 소유하는지 정해야 합니다.

### reference 종류

- strong/hard reference: 대상의 수명 또는 asset load를 유지
- weak reference: 대상이 사라질 수 있음을 허용
- soft reference: identity/path만 보관하고 필요할 때 resolve/load
- handle with generation: slot 재사용 뒤 stale access를 검출
- event subscription: 눈에 보이지 않는 reference이므로 해제 수명 필요

## 설계 계약

### lifecycle state를 명시합니다

```text
Allocated
→ Spawned
→ DependenciesAvailable
→ Initialized
→ Active
→ Disabled
→ Despawning
→ Destroyed
```

각 component가 `Active`에 도달하기 전 필요한 dependency를 작성합니다. network와 async loading이 있는 프로젝트에서 임의 delay 대신 state transition을 사용합니다.

### 생성과 등록을 분리합니다

constructor 또는 deserialization 중에는 다른 object가 준비되지 않았을 수 있습니다.

- allocation: memory와 기본값
- deserialization: authored data 복원
- dependency resolution: references 연결
- registration: system index·event bus 등록
- activation: gameplay update 참여

중간 실패 시 역순 cleanup이 가능해야 합니다.

### destroy는 사건입니다

`Destroy()`가 즉시 memory free를 뜻하지 않을 수 있습니다. 호출 뒤 허용되는 행동을 정합니다.

- new command 수신 금지
- collision/nav index에서 제거
- event unsubscribe
- child/owned resource 정리
- replication tombstone 또는 despawn event
- frame/job fence 뒤 memory reclaim

### pooling은 identity와 state reset 계약입니다

pool은 allocation 최적화일 뿐 객체를 새로 만든 것처럼 보이게 해야 합니다.

- generation 또는 spawn sequence를 갱신합니다.
- previous owner, timer, subscription, animation state를 reset합니다.
- external weak handle이 새 object로 오인되지 않게 합니다.
- debug build에서 dirty field를 검출합니다.

### streaming boundary를 data로 표시합니다

scene A가 scene B의 object를 hard reference하면 B를 unload하지 못할 수 있습니다. cross-scene 관계는 stable id, service query 또는 explicit dependency manifest로 표현합니다.

## 대표 실패

### initialization order를 파일 배치 순서에 의존합니다

editor hierarchy나 serialization order가 바뀌면 race가 발생합니다. dependency readiness를 명시합니다.

### event bus가 object를 살려 둡니다

listener를 unsubscribe하지 않아 scene unload 뒤 callback이 실행되거나 asset과 object가 resident로 남습니다.

### network id 또는 pool slot을 너무 빨리 재사용합니다

지연된 packet과 job completion이 새 entity에 적용됩니다. generation, epoch와 acknowledgement window를 둡니다.

### component가 서로의 private state를 직접 수정합니다

movement, animation, combat이 같은 transform·velocity·status를 각자 소유하면 update order에 따라 결과가 달라집니다. 정본 owner와 event/interface를 정합니다.

### async callback이 파괴된 owner를 캡처합니다

asset load나 save completion이 돌아왔을 때 world가 이미 unload됐을 수 있습니다. cancellation token, weak handle와 request generation을 사용합니다.

## 관찰과 검증

### lifecycle trace

```json
{
  "entity": "enemy:77#gen3",
  "world": "arena-a",
  "event": "lifecycle_transition",
  "from": "DependenciesAvailable",
  "to": "Initialized",
  "tick": 241,
  "reason": "nav-agent-ready"
}
```

### 필수 테스트

- scene load/unload를 반복해 entity·subscription·asset count가 기준선으로 돌아옵니다.
- initialization completion 순서를 섞어도 `Active` 전에 필요한 dependency가 모두 준비됩니다.
- destroy 요청 뒤 늦은 input·network·async completion이 무시됩니다.
- pool 재사용 뒤 이전 timer·owner·status가 남지 않습니다.
- hard reference graph가 streaming 목표를 깨지 않는지 content validator로 검사합니다.
- save/network id가 runtime handle과 분리돼 migration·reconnect에서 올바르게 resolve됩니다.

### leak과 stale reference 관찰

- world별 object count와 peak
- event subscriber count
- async request outstanding count
- asset reference chain
- pooled object dirty-field count
- destroyed handle access assertion

## 실습 연결

[월드 수명 검토 실습](../exercises/03-world-lifecycle-review/README.md)에서 비동기 load, scene unload와 delayed callback trace를 분석합니다.

## 기존 브랜치와 경계

- C++ object lifetime과 smart pointer는 `cpp`가 소유합니다.
- virtual memory와 process resource는 `operating-systems`가 소유합니다.
- 현재 문서는 engine world, scene streaming, entity identity, component registration과 deferred destruction 계약을 소유합니다.

## 완료 기준

- world, scene, entity, component, subsystem과 asset 수명을 분리합니다.
- initialization과 activation, destroy request와 reclaim을 다른 단계로 설계합니다.
- hard/weak/soft reference와 generation handle을 목적에 맞게 선택합니다.
- load/unload·pool·async completion의 대표 race를 trace와 검사로 재현합니다.
