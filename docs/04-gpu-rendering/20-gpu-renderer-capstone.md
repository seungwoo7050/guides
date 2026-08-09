# GPU renderer capstone

## 목표

소프트웨어 rasterizer의 scene·규약·artifact를 GPU renderer로 이전합니다. 단색 삼각형에서 끝나지 않고 resource upload, shader/pipeline, depth·texture·lighting, frame slot·resize, validation·capture와 profile을 하나의 재현 가능한 renderer 계약으로 완성합니다.

## 시작하기 전에

[소프트웨어 capstone](../02-software-rasterization/09-software-rasterizer-capstone.md)의 고정 fixture와 CPU reference가 있어야 합니다. GPU API를 먼저 구현했다면 최소한 transform·coverage·depth·color fixture를 별도 CPU 계산으로 준비합니다.

전체 요구사항은 [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md)의 설명과 `contract.json`을 함께 적용합니다. JSON은 artifact·invariant·mutation id의 기계 판독 정본이고, 이 문서의 구현 범위와 사람 검토를 대신하지 않습니다. 실행·capture 전에는 [안전 및 운영 계약](../../SAFETY.md)을 따릅니다.

### 현재 번들 reference가 증명하는 범위

| 증거 | 번들 reference의 자동 범위 | 최종 학습자 capstone에 추가할 근거 |
|---|---|---|
| 실제 GPU draw | macOS Metal/MSL offscreen RGBA8+D16, position·vertex color indexed triangle, readback과 fence | texture/sampler/material bind, normal·lighting shader와 debug attachment |
| scene 비교 | 동일 scene id/hash, primitive·extent, 고정 color/depth image의 제한된 byte tolerance | UV·normal·material input, linear lighting과 final encoding의 첫 차이 보고서 |
| 수명 | 같은 Metal device의 실제 2 slots·3 submits·12 events, completion 뒤 slot 0 재사용, zero-extent skip, 64×64→96×72 offscreen generation·readback·retire와 결정적 상태 모델 | window/swapchain resize·minimize·restore·high-DPI, 장시간 frames-in-flight, reload와 shutdown stress |
| debug | fatal/warning baseline, 추적 label/manifest, synthetic defect reports | 지원 capture tool의 실제 event/resource label과 driver message 조사 |
| 성능 | `required`에서는 실제 Metal offscreen workload의 CPU record/submit 및 submit-to-fence wall time, fallback에서는 결정적 report 형식 | 실제 GPU timestamp/counter, 대표 workload의 raw sample·환경과 측정 기반 변경 |

현재 `triangle.metal`과 `triangle.hlsl`은 position과 vertex color만 소비합니다. actual GPU reference의 성공은 texture, normal map, material 또는 lighting을 GPU로 옮겼다는 증거가 아닙니다. `resize-trace.json`에는 결정적 모델 사건과 실제 offscreen extent 전이가 함께 있지만 어느 쪽도 platform window/swapchain event는 아닙니다. 아래 범위는 **학습자가 완료해야 할 목표**이고 자동 reference 범위를 설명하는 목록이 아닙니다.

## 범위

필수:

- SDL3 window와 GPU device 또는 동등한 명시적 API profile
- backend/shader format/device 정보 artifact
- vertex/index/uniform upload
- color + depth render pass
- opaque textured material
- 한 directional light 또는 동등한 단순 lighting
- camera와 object transform
- frame slot 2개 이상
- resize/zero extent 처리
- validation/debug label
- screenshot readback 또는 capture 가능한 output
- software/GPU 비교 보고서
- CPU/GPU timing과 workload 통계

선택:

- transparent queue
- mipmap과 normal map
- frustum culling/LOD
- shader hot reload
- offscreen/post-process pass
- resource cache와 deferred destruction 일반화

선택 기능 때문에 필수 state와 검증이 숨으면 제거합니다.

## 권장 구조

```text
renderer/
├── device/          backend, capability, error
├── resources/       buffer, texture, sampler, generation, retire
├── shaders/         build manifest, reflection, binary
├── pipelines/       complete key와 cache
├── frame/           slots, command, acquire, submit, resize
├── scene/           validated render snapshot
├── passes/          upload, opaque, optional transparent/readback
├── debug/           labels, validation, capture metadata
└── metrics/         CPU/GPU timing과 work counters
```

API wrapper를 만들기 위해 모든 함수와 enum을 다시 추상화하지 않습니다. 다음 경계가 실제로 필요할 때만 wrapper를 둡니다.

- lifetime과 deferred destruction
- backend-independent scene/resource descriptor
- shader/pipeline manifest
- frame slot과 completion
- test에서 교체할 artifact/readback

## 단계별 구현

### 1. device와 clear frame

window, device, swapchain texture를 획득해 고정 clear color를 표시합니다. device/backend/shader format, extent와 swapchain generation을 기록합니다. resize와 zero extent를 이 단계에서 먼저 처리합니다.

### 2. 단색 triangle

고정 vertex buffer와 최소 shader/pipeline을 사용합니다. vertex output clip coordinate를 CPU 정본과 대조합니다. culling, depth와 blending은 처음에는 명시적 단순 상태로 둡니다.

### 3. indexed mesh와 transform

index buffer와 frame/object uniform을 추가합니다. frame slot마다 다른 object transform marker를 사용해 overwrite 오류를 검사합니다.

### 4. depth와 여러 object

depth attachment, clear, compare와 write를 추가합니다. draw order를 바꿔도 opaque visibility가 같아야 합니다. primitive id 또는 debug color로 software reference와 비교합니다.

### 5. texture와 material

corner marker와 checker texture를 upload하고 sampler를 bind합니다. sRGB color와 data texture를 구분하고 perspective UV 결과를 비교합니다.

### 6. lighting

world/view 공간을 정하고 normal matrix, directional light와 linear color를 shader에 연결합니다. normal·NdotL·base color debug mode를 제공합니다.

### 7. lifecycle와 readback

두 개 이상의 frame slot, completion 기반 재사용, resize generation과 screenshot readback을 구현합니다. 이전 attachment/resource는 last-use completion 뒤 retire합니다.

### 8. debug와 performance

pass/draw/resource label, validation baseline과 한 frame capture를 남깁니다. CPU frame 구간과 GPU pass timestamp를 분리하고 최소 세 workload를 측정합니다.

번들 report의 `submit_to_fence_ns`는 submit 직전부터 fence wait 반환까지의 CPU wall time이며 GPU pass timestamp가 아닙니다. `--gpu required`의 세 workload는 실제 Metal offscreen submit/fence를 반복하지만 작은 proxy scene이며, `lifecycle-sim` fallback은 결정적 모델 sample입니다. 어느 쪽도 GPU timestamp나 대표 제품 workload 없이 실제 GPU 병목 결론을 증명하지 않습니다.

## 비교 정책

### 정확히 같아야 하는 항목

- scene/object/material id와 draw 입력
- transform convention과 projection parameter
- primitive 수, culling 의도와 attachment extent
- shader/pipeline manifest
- output channel/encoding/alpha 의미

### 허용 오차가 필요한 항목

- interpolated float depth/color
- shader compiler와 GPU 연산 순서 차이
- texture filtering의 제한된 edge 차이

비교 보고서는 다음 순서를 사용합니다.

1. environment와 artifact hash
2. primitive/coverage 차이
3. depth 차이
4. UV/normal/material input 차이
5. linear color 차이
6. final sRGB image 차이
7. 허용 mask와 이유

경계 전체를 넓은 tolerance로 제외하지 않습니다. 차이가 규약 차이인지 수치 차이인지 작은 pixel trace로 설명합니다.

## 실패 주입

최소한 다음 mutation을 한 번씩 검증합니다.

- vertex stride 또는 attribute format 오류
- shader binding slot 오류
- pipeline target/depth format 오류
- uniform frame slot overwrite
- upload 완료 전 staging 재사용
- resize 뒤 old depth attachment 사용
- sRGB/data texture format 교환
- culling/front-face 반전
- blend factor 오류

validation이 잡는 mutation과 image/test가 잡는 mutation을 구분합니다. 모든 오답이 API validation으로 검출되지는 않습니다.

번들 GPU mutation은 잘못된 state를 driver에 제출하지 않고 계약 경계에서 안전하게 거부하며 `mutation-diagnostic.json`에 `executed_on_gpu: false`를 기록합니다. 이 음성 대조군은 false invariant와 진단 경로를 검증하지만, 실제 driver validation이 해당 오답을 잡았다는 증거는 아닙니다.

## 성능 제출물

세 workload 예:

1. 작은 object 다수: CPU submission/driver 관찰
2. 큰 fullscreen/고해상도: fragment·bandwidth 관찰
3. triangle·material이 많은 scene: geometry/state 변화 관찰

각 workload에 다음을 기록합니다.

- extent, draw/triangle/resource 수
- CPU median/p95와 주요 구간
- GPU pass median/p95
- validation/capture on/off
- image hash와 correctness 상태
- 적용한 최적화 한 가지와 전후 근거

최적화가 없어도 병목이 없다는 근거가 명확하면 됩니다. 억지로 성능을 바꾸지 않습니다.

## 완료 보고서

```text
1. 범위와 비범위
2. 좌표·색·alpha·sample 규약
3. renderer architecture와 상태 소유권
4. resource/frame lifecycle
5. shader/pipeline build 계약
6. software/GPU 비교 결과
7. validation·capture 조사 사례
8. performance budget
9. 알려진 한계와 후속 프로젝트
```

## 연결 실습

- [`06-gpu-first-frame`](../../exercises/06-gpu-first-frame/README.md)
- [`07-frame-debugging`](../../exercises/07-frame-debugging/README.md)
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md)

## 완료 기준

- 같은 scene 계약을 CPU와 GPU renderer가 소비합니다.
- resource upload·pipeline·frame slot·resize·readback 수명을 completion과 generation으로 관리합니다.
- validation, frame capture와 단계별 attachment로 알려진 오답을 거부합니다.
- software/GPU 차이를 coverage·depth·attribute·linear color·output 순서로 설명합니다.
- CPU/GPU frame budget과 한 가지 측정 기반 변경을 재현 가능한 보고서로 남깁니다.

`--gpu required` 자동 검사만으로 위 목록 전체를 완료 처리하지 않습니다. 자동 검사에서는 actual GPU 실행 여부, scene/color/depth 비교, manifest·lifecycle·validation·report schema와 known-bad 거부를 확인합니다. 사람 검토에서는 texture/material/lighting GPU 경로, 실제 window/swapchain resize·minimize·high-DPI와 capture, 진짜 GPU timestamp, tolerance 이유와 한계가 있는지 확인합니다. 지원 환경 때문에 항목을 실행하지 못했다면 대체 상태 모델과 그 한계를 함께 제출하되 “통과”로 바꾸어 쓰지 않습니다.
