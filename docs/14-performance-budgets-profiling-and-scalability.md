# 성능 예산, profiling과 scalability

## 문제

게임 성능은 “최적화했다” 또는 “60 FPS가 나온다”는 한 문장으로 설명할 수 없습니다. target device, scene, player action, thermal state, build option과 측정 도구가 달라지면 결과가 달라집니다. 평균 FPS는 hitch, input latency, memory peak, loading stall과 bandwidth spike를 숨깁니다.

성능 작업은 다음 순서여야 합니다.

```text
player experience 목표
→ target hardware와 representative workload
→ subsystem budget
→ profile과 critical path
→ 병목 가설
→ 한 변경
→ 같은 조건 재측정
→ 품질·correctness 회귀 확인
```

## 핵심 상태

### frame pipeline

일반적으로 다음 stage가 겹치거나 기다립니다.

- input sampling
- main/game thread simulation
- job/worker tasks
- render preparation/submission
- GPU execution
- present/display
- audio thread
- streaming/decompression
- network processing

CPU total 합보다 critical path와 synchronization wait가 frame time을 결정합니다.

### 성능 예산

| 자원 | 측정 예 | player impact |
|---|---|---|
| CPU frame | main/render/job ms, p95/p99 | frame rate, input latency |
| GPU frame | pass별 GPU ms | frame rate, resolution/quality |
| memory | resident, peak, fragmentation | crash, OS eviction, stutter |
| allocation | per-frame alloc, GC pause | hitch |
| loading | time to control, streaming stall | waiting, traversal hitch |
| disk/download | package/chunk size | install/update time |
| network | bytes/s, packet rate, correction | latency, data cost |
| battery/thermal | power, clock throttling | sustained performance |

### frame time과 FPS

FPS는 reciprocal이라 평균하기 어렵습니다. frame-time distribution을 사용합니다. 60Hz 목표라면 16.67ms가 전체 budget이지만 CPU와 GPU가 pipelined될 수 있으므로 각 thread·stage 관계를 profile로 확인합니다.

### scalability

quality setting은 단순 graphics preset이 아닐 수 있습니다.

- resolution/upscaling
- shadow, effect, animation LOD
- entity/AI update frequency
- streaming distance와 texture mip
- audio voices
- network update frequency는 gameplay 영향 검토 필요

quality를 낮춰도 중요한 gameplay 정보와 accessibility cue가 사라지지 않아야 합니다.

## 설계 계약

### target matrix를 먼저 정합니다

```text
platform/device class
resolution/display mode
quality profile
power/thermal mode
scene and duration
player/bot count
network condition
build type
capture tool/version
```

editor profile은 빠른 가설 생성용이고, release-like build를 target device에서 측정해 결론을 냅니다.

### representative workload를 버전 관리합니다

- dense combat scene
- worst-case camera path
- loading transition
- inventory/menu stress
- multiplayer player/bot count
- long soak session

content 변경으로 workload가 쉬워지거나 어려워질 수 있으므로 manifest와 expected range를 기록합니다.

### budget owner를 둡니다

각 subsystem에 예산과 escalation rule을 둡니다. 예산은 팀 간 협상 가능한 계약이지 다른 팀을 벌주는 숫자가 아닙니다.

```text
animation main-thread p95 <= X ms
streaming peak memory <= Y MB
world transition control-ready <= Z sec
```

### 측정 전후 correctness를 보존합니다

object pooling, lower tick rate, culling과 async job으로 성능을 개선하면서 stale state, fairness와 event ordering을 깨뜨릴 수 있습니다. 동일 regression fixture를 실행합니다.

### optimization hierarchy를 사용합니다

1. 불필요한 작업 제거
2. frequency/visibility/LOD 감소
3. algorithm과 data structure 개선
4. allocation과 data layout 개선
5. parallelism/vectorization
6. low-level tuning

profile 없이 마지막 단계부터 시작하지 않습니다.

### hitch와 steady-state를 분리합니다

first use shader/PSO, asset decompression, GC, save, log flush와 network burst는 평균 비용이 낮아도 큰 hitch를 만듭니다. occurrence와 maximum/p99를 추적합니다.

## 대표 실패

### editor에서만 profile합니다

editor object, instrumentation, asset path와 CPU/GPU 환경이 target build와 다릅니다.

### 평균 FPS만 보고 완료합니다

몇 초마다 100ms hitch가 있어도 평균은 높을 수 있습니다. frame-time percentile과 longest frame을 봅니다.

### profiler overhead를 무시합니다

deep profiling과 full trace가 timing을 바꿉니다. low-overhead capture와 focused capture를 구분합니다.

### CPU와 GPU를 동시에 추측합니다

먼저 frame이 CPU-bound, GPU-bound, sync-bound, I/O-bound인지 확인합니다.

### microbenchmark 개선을 전체 frame 개선으로 오인합니다

critical path에 없거나 workload가 대표적이지 않을 수 있습니다. full scenario를 재측정합니다.

### memory steady state만 봅니다

world transition, screenshot, save, shader compilation과 content import peak에서 crash합니다.

### quality reduction이 gameplay를 바꿉니다

enemy, telegraph, subtitle, contrast cue를 cull하거나 AI update를 낮춰 fairness를 바꿉니다.

## 관찰과 검증

### profile review

1. capture의 build/device/content/workload를 확인합니다.
2. 목표 frame budget 초과 구간을 찾습니다.
3. CPU/GPU/I/O critical path를 구분합니다.
4. 가장 큰 contributor와 wait reason을 찾습니다.
5. 병목 가설과 예상 효과를 기록합니다.
6. 변경 뒤 같은 capture를 비교합니다.
7. correctness와 quality regression을 검사합니다.

### 성능 회귀 gate

- representative benchmark의 median/p95/p99
- 허용 noise와 sample count
- hardware pool과 thermal warm-up
- baseline update 승인 절차
- fail, warn, investigate threshold

CI의 가상 machine에서 모든 GPU 성능을 판단할 수 없습니다. target hardware lab 또는 반복 가능한 manual capture를 포함합니다.

### memory 검사

- world별 resident breakdown
- asset/reference chain
- allocation rate와 GC
- fragmentation/heap class
- transition peak
- unload 뒤 baseline 회복
- long soak growth

### network와 loading

- command/snapshot bytes와 packet rate
- correction rate와 bandwidth relation
- time to first interaction
- streaming request queue·miss·stall
- patch/depot size와 file churn

## 실습 연결

[성능 예산 검토 실습](../exercises/07-performance-budget-review/README.md)에서 target device profile을 분석해 병목·예산·검증 계획을 작성합니다.

## 기존 브랜치와 경계

- cache, SIMD와 CPU 구조는 `computer-architecture`가 소유합니다.
- algorithm complexity는 `algorithms`가 소유합니다.
- GPU pipeline은 `computer-graphics`가 소유합니다.
- 현재 문서는 player experience를 target-device frame·memory·loading·network budget으로 바꾸고 profile 근거로 검증하는 과정을 소유합니다.

## 완료 기준

- target device, build, content와 workload가 포함된 성능 주장을 작성합니다.
- 평균 FPS 대신 frame-time distribution, hitch와 critical path를 분석합니다.
- CPU·GPU·memory·loading·network 예산에 owner와 regression gate를 둡니다.
- 최적화 뒤 correctness·quality와 target-device 결과를 같은 조건에서 재검증합니다.
