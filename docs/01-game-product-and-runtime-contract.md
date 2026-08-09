# 게임 제품과 runtime 계약

## 문제

게임은 단일 executable이더라도 하나의 상태만 가지지 않습니다. boot, patch 확인, sign-in, menu, lobby, world loading, active play, pause, result, suspend, reconnect와 shutdown이 서로 다른 자원과 권한을 가집니다. 이 구분 없이 기능을 붙이면 다음 문제가 생깁니다.

- 메뉴에서 만든 singleton이 match 종료 뒤에도 이전 상태를 보존합니다.
- loading 실패와 gameplay 실패가 같은 오류 처리로 합쳐집니다.
- player profile, save slot, match state와 화면 widget이 서로의 정본이 됩니다.
- editor에서는 되지만 packaged build의 boot 순서에서 실패합니다.
- 재접속, map travel, suspend/resume과 hot reload에서 객체 수명이 뒤틀립니다.

게임 기능을 구현하기 전에 **제품 수명과 play session 수명**을 구분해야 합니다.

## 핵심 상태

### 제품 수준 상태

```text
ColdStart
→ PlatformInit
→ ContentReady
→ UserReady
→ Frontend
→ SessionJoining
→ WorldLoading
→ Playing
→ Results
→ Frontend
→ Suspending / ShuttingDown
```

실제 프로젝트의 상태 이름은 다를 수 있지만 각 전이는 다음을 가져야 합니다.

- 전이를 요청할 수 있는 actor
- 필요한 precondition
- 생성하거나 유지할 state
- 취소·timeout·실패 상태
- 완료를 알리는 event
- 이전 상태의 cleanup 책임

### 서로 다른 수명

| 수명 | 예 | 종료 사건 |
|---|---|---|
| process | engine runtime, platform service adapter | executable 종료 |
| user session | signed-in account, entitlement, settings | sign-out 또는 user switch |
| frontend | menu model, party/lobby view | match 진입 또는 app 종료 |
| world | map, scene graph, world subsystem | travel 또는 unload |
| match | rules, score, objective, authoritative actors | match result 확정 |
| entity | character, projectile, pickup | despawn 또는 owner 제거 |
| frame | temporary query/result/render command | frame fence 또는 scope 종료 |

같은 “manager”라는 이름을 사용해도 수명이 다르면 같은 객체에 넣지 않습니다.

### 상태의 정본과 view

- **authoritative state**: 규칙상 실제 결과를 결정하는 상태
- **derived state**: authoritative state로부터 다시 계산 가능한 값
- **presentation state**: animation, camera, HUD처럼 사용자에게 보이기 위한 상태
- **cached state**: 비용을 줄이기 위해 보관하지만 무효화 규칙이 필요한 값
- **editor state**: 제작 과정에서만 존재하는 metadata와 selection
- **telemetry state**: 관찰용 event이며 gameplay 정본이 아님

“점수는 HUD text에 있다”, “현재 stage는 scene 이름이다” 같은 설계는 표현이나 자원 배치를 정본으로 오인한 것입니다.

## 설계 계약

### runtime context를 명시합니다

한 기능을 검토할 때 최소한 다음 context를 기록합니다.

```text
process id / build id
platform and device class
local user id
session id
world id
match id
entity id
simulation tick
render frame
content version
save schema version
```

모든 로그에 전부 넣을 필요는 없지만, 문제가 어느 수명에 속하는지 재구성할 식별자는 있어야 합니다.

### transition은 요청과 완료를 분리합니다

`LoadWorld()` 호출이 곧 world가 playable하다는 뜻은 아닙니다.

```text
request accepted
→ dependency discovery
→ I/O and deserialize
→ object creation
→ cross-reference resolution
→ gameplay initialization
→ presentation readiness
→ player control enabled
```

호출자는 필요한 readiness 수준을 선택해야 합니다. 렌더링 가능한 상태와 gameplay interaction 가능한 상태가 같지 않을 수 있습니다.

### vertical slice를 상태 경계로 정의합니다

vertical slice는 기능 목록이 아니라 다음을 end-to-end로 연결하는 최소 제품 조각입니다.

```text
입력
→ 게임 규칙
→ 월드 상태
→ 표현
→ 저장 또는 세션 결과
→ 테스트·telemetry
→ target build
```

예를 들어 “공격 버튼과 animation이 있다”만으로는 vertical slice가 아닙니다. hit 판정, cooldown, death, restart, save/network 영향과 실패 재현이 빠졌기 때문입니다.

### engine callback보다 project contract가 우선합니다

`BeginPlay`, `Awake`, `_ready` 같은 callback은 엔진이 제공하는 사건일 뿐입니다. 프로젝트는 그 시점에 무엇이 준비됐는지 별도로 정의해야 합니다.

```text
Spawned
→ DependenciesAvailable
→ GameplayInitialized
→ PresentationReady
→ Active
→ Deactivating
→ Destroyed
```

network replication, async asset와 scene streaming이 들어오면 하나의 callback만으로 준비 상태를 보장하기 어렵습니다.

## 대표 실패

### 전역 singleton에 서로 다른 수명을 저장합니다

process 동안 유지되는 객체가 match-specific pointer를 계속 보관하면 travel 뒤 stale reference가 됩니다. 해결은 singleton 제거 자체가 아니라 **수명별 owner와 reset 사건을 명시하는 것**입니다.

### 화면이 상태 전이를 결정합니다

결과 화면이 열렸기 때문에 match가 끝났다고 판단하면 UI 실패가 규칙 실패로 전파됩니다. match result가 확정되고 UI가 그 event를 표현해야 합니다.

### 초기화 순서를 임의 delay로 맞춥니다

“0.5초 뒤 실행”은 dependency readiness를 증명하지 않습니다. 느린 device, packet delay와 content miss에서 다시 실패합니다. 필요한 state가 준비됐다는 event 또는 future를 사용합니다.

### editor path를 runtime path로 가정합니다

editor는 asset database, hot reload, loose file과 추가 process를 가집니다. packaged build는 cooked asset, platform sandbox와 다른 startup order를 사용합니다. 두 환경의 성공 조건을 분리합니다.

### 실패 뒤 partial state가 남습니다

world load 중 일부 subsystem만 등록된 상태에서 frontend로 돌아가면 다음 진입이 중복 registration 또는 leaked resource로 실패합니다. transition마다 rollback/cleanup owner가 필요합니다.

## 관찰과 검증

### runtime state trace

transition마다 다음 event를 남깁니다.

```json
{
  "event": "runtime_transition",
  "from": "WorldLoading",
  "to": "Playing",
  "request_id": "load-42",
  "world_id": "arena-01",
  "content_version": "2026.08.1",
  "duration_ms": 1842,
  "result": "success"
}
```

동일한 request id로 시작·진행·완료·실패를 연결합니다.

### 상태 전이 검사

- 허용되지 않은 transition은 명시적으로 거부합니다.
- transition 취소 뒤 새 world·entity·asset handle이 남지 않는지 검사합니다.
- user switch, reconnect, suspend와 shutdown을 정상 입력으로 테스트합니다.
- menu→play→menu→play 반복에서 resource와 callback 수가 증가하지 않는지 봅니다.
- editor와 packaged build에서 최소 boot smoke를 각각 실행합니다.

### ownership map

각 주요 state에 대해 표를 작성합니다.

| state | owner | created | valid until | serialized | replicated | observed by |
|---|---|---|---|---|---|---|
| match score | rules subsystem | match start | result commit | replay/result | yes | HUD, telemetry |

빈칸이나 “여러 곳”이 많으면 책임 경계가 아직 결정되지 않은 것입니다.

## 실습 연결

[월드와 객체 수명 실습](../exercises/03-world-lifecycle-review/README.md)에서 startup·streaming·destroy event를 분석합니다. Capstone에서는 `runtime-state-map.md`에 process, frontend, world, match와 entity 수명을 모두 기록합니다.

## 기존 브랜치와 경계

- 객체 수명과 RAII 구현은 `cpp`가 소유합니다.
- process, thread, virtual memory와 filesystem 수명은 `operating-systems`가 소유합니다.
- 공개 서비스의 deployment state는 `web-infra`가 소유합니다.
- 현재 문서는 그 기반을 게임의 process·world·match·frame 수명에 적용합니다.

## 완료 기준

- 제품 boot에서 shutdown까지 상태와 실패 transition을 그릴 수 있습니다.
- player, world, match, entity와 presentation state의 owner를 구분합니다.
- 엔진 callback에 의존하지 않는 readiness와 cleanup 계약을 작성합니다.
- vertical slice를 입력·규칙·표현·검증·빌드까지 연결해 정의합니다.
