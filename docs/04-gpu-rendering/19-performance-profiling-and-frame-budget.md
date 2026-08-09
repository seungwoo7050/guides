# 성능·profiling·frame budget

## 목표

FPS 하나나 평균 실행 시간으로 renderer 성능을 판단하지 않고, frame budget을 CPU 준비·command 기록·GPU pass·대역폭·동기화·present로 분해합니다. 결과 계약을 보존한 채 병목 가설을 세우고, 측정 환경·분포·GPU timestamp·capture 근거로 변경을 검증합니다.

## 시작하기 전에

일반 CPU cache·SIMD·멀티코어 성능 모델은 [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)가 소유합니다. 여기서는 graphics workload와 GPU pipeline에 적용합니다.

### frame time과 FPS

```text
FPS = 1 / frame_time_seconds
```

60 FPS는 약 16.67 ms, 120 FPS는 약 8.33 ms의 frame time에 해당합니다. FPS 차이는 비선형이므로 최적화 전후를 ms로 비교합니다.

평균만 보지 않습니다.

- median
- p90/p95/p99
- 최대값과 hitch frequency
- warm-up과 shader/pipeline creation frame
- CPU/GPU 각각의 frame time

vsync/present limit 때문에 GPU가 빨라도 FPS가 고정될 수 있습니다. benchmark 모드와 실제 present 모드를 구분합니다.

### frame budget 표

```text
CPU
- scene update/snapshot
- culling/LOD
- command building
- upload preparation
- submission/present wait

GPU
- transfer
- geometry/opaque
- transparent
- post-process
- readback/present 관련 wait
```

CPU와 GPU가 겹쳐 실행되므로 단순 합이 화면 간격과 같지 않을 수 있습니다. queue timeline과 frames-in-flight를 함께 봅니다.

### CPU-bound와 GPU-bound

해상도를 크게 낮췄을 때 frame time이 거의 변하지 않으면 CPU 또는 geometry/driver overhead를 의심할 수 있습니다. 반대로 pixel 수와 함께 크게 줄면 fragment·bandwidth·render target 비용일 수 있습니다. 이는 가설 도구이지 단독 증명은 아닙니다.

검사 실험:

- resolution scale 변경
- draw/triangle 수 고정·변경
- shader를 단순화하되 같은 geometry/state 유지
- texture 해상도/format 변경
- culling off/on
- GPU idle wait 제거/주입 비교

각 실험에서 image 계약이 의도한 범위 외에 바뀌지 않았는지 확인합니다.

### GPU timestamp

GPU timestamp query가 지원되면 pass 시작/끝에 기록하고 query 결과를 completion 뒤 읽습니다. CPU wall clock으로 command recording 구간을 재서 GPU 실행 시간이라고 부르지 않습니다.

주의:

- timestamp period와 단위 변환
- query availability/completion
- capture/validation이 timing에 미치는 영향
- queue 간 timestamp 비교 가능성
- 너무 많은 query의 overhead

### pipeline 통계와 work 지표

가능한 경우 다음을 수집합니다.

- draw/dispatch 수
- submitted/culled triangle
- vertex invocation
- fragment/shader invocation
- depth rejection과 overdraw 추정
- texture/resource bytes와 format
- upload bytes
- pipeline switch와 bind 수

하드웨어 counter의 의미와 지원 여부는 GPU마다 다릅니다. tool이 보여 주는 counter 이름만으로 물리 원인을 단정하지 않습니다.

### 병목 유형

#### submission/driver overhead

작은 draw가 매우 많고 CPU command 시간이 큰 경우 batching, instancing, state sorting 또는 GPU-driven 경로를 검토합니다. draw 수 감소가 memory·culling·복잡한 shader 비용을 늘릴 수 있으므로 전체 결과를 측정합니다.

#### vertex/geometry

너무 많은 visible triangle, poor LOD, 중복 vertex transform, 작은 primitive와 clipping이 원인일 수 있습니다. triangle count만 아니라 screen coverage와 primitive size를 봅니다.

#### fragment/overdraw

고해상도, 큰 fullscreen pass, transparent layer, expensive shader와 depth reject 부족이 원인일 수 있습니다. depth prepass는 모든 scene에서 이득이 아니며 extra geometry/pass 비용과 비교합니다.

#### texture/bandwidth

큰 format, cache-poor access, 과도한 render target, high sample count와 upload가 원인일 수 있습니다. texture compression과 format 변경은 품질·platform support와 함께 검토합니다.

#### synchronization

매 frame GPU idle, readback, query wait와 frame slot 부족이 CPU/GPU overlap을 막을 수 있습니다. wait call 자체가 아니라 timeline의 빈 구간과 dependency 필요성을 확인합니다.

#### allocation/pipeline compilation

frame 중 resource allocation, shader compilation, pipeline creation과 asset decode는 hitch를 만듭니다. cache와 prewarm은 key·version·memory budget 계약이 완전할 때 적용합니다.

### benchmark 설계

- 고정 scene·camera·extent·backend·shader hash
- warm-up 구간과 측정 구간 분리
- 여러 번 반복하고 distribution 저장
- power/thermal 상태와 background load 기록 가능 시 포함
- debug/validation/capture 상태 기록
- correctness artifact hash 확인
- raw sample을 보관하고 요약만 남기지 않음

서로 다른 GPU의 숫자를 절대 등급처럼 비교하지 않습니다. 변경 전후 같은 환경에서 가설을 검증합니다.

### 최적화 순서

```text
정확성 기준 고정
→ 실제 frame과 병목 구간 측정
→ 한 가지 원인 가설
→ 최소 변경
→ 이미지·상태 회귀 검사
→ CPU/GPU 분포 재측정
→ memory·복잡도·이식성 비용 기록
```

`reserve`, batching, multithreading, SIMD, async upload 같은 기술 이름을 먼저 선택하지 않습니다.

## 연결 실습

- [`07-frame-debugging`](../../exercises/07-frame-debugging/README.md): frame timing과 draw/attachment/capture 근거를 하나의 보고서로 만듭니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): 최소 세 workload에서 CPU/GPU budget과 한 가지 검증된 개선을 제출합니다.

## 완료 기준

- FPS 대신 frame time distribution과 budget을 사용합니다.
- CPU recording과 GPU execution 시간을 서로 다른 clock과 completion으로 측정합니다.
- resolution·workload 변형으로 병목 가설을 만들고 counter/capture로 확인합니다.
- 최적화 전후 image·state 계약, memory와 complexity 비용을 함께 기록합니다.
