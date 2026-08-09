# 테스트, 디버깅, telemetry와 재현

## 문제

게임 버그는 시간·입력·content·device·network·random·thread와 player action이 결합돼 재현하기 어렵습니다. “10분쯤 플레이하면 가끔 죽는다”는 보고를 코드 한 줄로 고치려 하면 추측과 회귀가 반복됩니다.

게임 품질 시스템의 목표는 모든 화면을 자동 클릭하는 것이 아니라 다음 흐름을 짧게 만드는 것입니다.

```text
관찰된 증상
→ build/content/device/session 식별
→ input/event/state trace
→ 최소 재현
→ 첫 잘못된 transition
→ 수정
→ regression fixture
→ target build 재검증
```

이 장의 소유 범위는 일반적인 관측 플랫폼이나 사고 대응이 아닙니다. `game-development`의 “게임플레이 기능의 상태 전이·저장·재현·테스트”와 “frame budget·profiling·client/server authoritative 경계의 게임 맥락”을 실행 가능한 증거로 만드는 데 집중합니다.

## 핵심 상태

### 테스트 층

| 층 | 검사 대상 | 예 |
|---|---|---|
| pure rule | 상태 전이와 invariant | damage, cooldown, inventory |
| simulation | tick·command·world fixture | movement, combat, AI |
| component/system | engine integration | asset load, physics, save |
| scene/level | authored content와 lifecycle | spawn, objective, streaming |
| multi-instance | network authority와 convergence | join, correction, reconnect |
| platform/build | package, suspend, input, storage | target device smoke |
| playtest | feel, readability, balance | player experience |

자동화는 correctness와 재현을 강화하지만 재미·접근성·feel 판단을 완전히 대신하지 않습니다.

### bug evidence

최소한 다음을 함께 수집합니다.

- build id와 source revision
- content manifest와 rule version
- platform/device/quality profile
- session/world/match/entity id
- simulation tick과 render frame
- input or command trace
- relevant state hash/snapshot
- network conditions
- last transitions/events
- crash stack/minidump 또는 hang trace

### telemetry 종류

- structured event: semantic transition
- metric: rate, duration, count, distribution
- trace/span: request·load·transition 연결
- log: local detail와 diagnostics
- crash/hang capture
- replay/input trace
- profile capture

각 도구가 보장하는 것과 cost/privacy를 구분합니다.

## 설계 계약

### test seam을 runtime 설계에 포함합니다

- clock injection
- deterministic random stream
- command input fixture
- content manifest selection
- network fault injection
- headless simulation
- state snapshot/hash
- fake platform storage/service

제품 code와 전혀 다른 “test-only simulation”을 만들지 않고 같은 rule core를 사용합니다.

### assertion은 invariant와 context를 남깁니다

```text
ASSERT inventory.balance >= 0
player=p7 match=m12 tick=884
last_commands=[purchase:item42, cancel:item42]
rule_version=economy@8
```

release에서는 crash 대신 safe recovery가 필요할 수 있지만 evidence를 잃지 않게 합니다.

### record/replay를 조사 도구로 사용합니다

전체 video만으로 내부 state를 알 수 없습니다. bounded command/event trace와 periodic state hash를 기록하면 first divergence를 찾을 수 있습니다. 개인정보와 storage cost를 제한합니다.

### bug report를 실행 가능한 계약으로 바꿉니다

```text
Given build/content/device
And initial snapshot
When command trace is applied
Then invariant X breaks at tick Y
And expected transition Z does not occur
```

### telemetry schema를 versioning합니다

field 의미, unit, optionality, cardinality와 개인정보 분류를 기록합니다. event 이름 재사용으로 의미를 바꾸지 않습니다.

### 관측이 gameplay를 바꾸지 않게 합니다

logging lock, allocation과 profile instrumentation이 timing을 바꿀 수 있습니다. debug와 release capture 차이를 기록하고 low-overhead path를 둡니다.

### 수정 전후에 같은 근거를 사용합니다

재현만 성공하고 수정을 검증하지 않으면 세 번째 종료 능력을 입증하지 못합니다. 같은 build mode, content, command trace, target profile과 측정 구간을 고정한 뒤 다음 묶음을 남깁니다.

```text
known-bad fixture와 first wrong transition
→ 수정 가설과 변경
→ 같은 fixture의 invariant 회복
→ 같은 profile의 frame/resource 지표 비교
→ 회귀 fixture와 아직 보장하지 않는 범위
```

수정 뒤 평균 FPS만 좋아졌거나 다른 scene·device를 측정했다면 같은 문제를 고쳤다는 근거로 사용하지 않습니다.

## 대표 실패

### screenshot과 서술만 있는 bug report

state, build와 input sequence가 없어 재현이 불가능합니다. in-game diagnostics/export 기능을 고려합니다.

### sleep으로 async test를 맞춥니다

느린 machine에서 flaky하고 빠른 machine에서 불필요하게 느립니다. readiness event, fake clock와 bounded polling을 사용합니다.

### golden image만으로 gameplay correctness를 판정합니다

화면은 같아도 내부 state가 다르거나 platform rendering 차이로 noise가 큽니다. semantic state와 image test를 목적별로 조합합니다.

### telemetry event가 너무 높은 cardinality를 가집니다

entity id, raw text와 unbounded asset path를 metric label로 사용하면 비용과 privacy 문제가 생깁니다.

### crash fix 뒤 regression test가 없습니다

특정 content와 command sequence가 다시 들어오면 재발합니다. 최소 fixture를 보존합니다.

### test가 실제 public path를 우회합니다

private field를 직접 설정해 initialization, authority와 validation bug를 놓칩니다. 가능한 한 command/API/asset path를 사용합니다.

## 관찰과 검증

### 최소 재현 축소

1. build와 content를 고정합니다.
2. save/world snapshot을 줄입니다.
3. input/event trace를 binary search 또는 delta debugging합니다.
4. presentation과 optional subsystem을 끕니다.
5. first bad tick/event를 찾습니다.
6. 해당 invariant를 pure/simulation test로 옮깁니다.

### flaky test 조사

- seed와 scheduling 기록
- timeout과 actual duration
- shared global state
- asset cache/warm state
- thread/job completion order
- network fault seed
- test order dependence

retry로 숨기기 전에 flake를 별도 failure로 관리합니다.

### test quality meta-check

- expected assertion을 반대로 바꾸면 test가 실패합니까?
- known-bad fixture가 실제로 거부됩니까?
- telemetry field를 제거하면 schema check가 실패합니까?
- replay command 하나를 바꾸면 hash가 달라집니까?
- test가 source state를 오염시키지 않습니까?

## 실습 연결

모든 실습이 bug evidence와 validation을 요구합니다. Capstone에서는 `test-and-observability-plan.md`, `reproduction-bundle/`과 replay hash를 제출합니다.

## 기존 브랜치와 경계

- 언어별 unit test와 debugger는 각 언어 브랜치가 소유합니다.
- 서비스 관측성과 사고 대응은 `web-infra`·`cybersecurity`가 소유합니다.
- 현재 문서는 game tick, content, input, replay, target device와 multi-instance를 결합해 게임플레이 상태 전이·저장·재현·테스트와 profiling 근거를 검증합니다.

## 완료 기준

아래 항목은 게임플레이 재현·테스트와 profiling 기반 수정 종료 능력의 근거입니다.

- rule, simulation, scene, network, platform와 playtest 층을 구분합니다.
- bug report를 build/content/state/input/tick 근거를 가진 fixture로 바꿉니다.
- record/replay와 state hash로 first divergence를 찾습니다.
- telemetry schema, privacy, cardinality와 meta-test를 포함한 관측 계약을 설계합니다.
- 같은 fixture와 profile로 수정 전후 invariant·frame·resource 결과를 비교해 “frame·resource·simulation 실패를 재현하고 profiling 근거로 수정한다”는 종료 능력을 입증합니다.
