# debugging·validation·frame capture

## 목표

검은 화면, 깨진 geometry, 깜빡임과 device 오류를 shader를 임의로 바꾸며 추측하지 않고, validation message·debug label·frame capture·중간 attachment·software reference를 이용해 **첫 잘못된 상태**까지 좁힙니다. 도구 출력이 증명하는 것과 증명하지 못하는 것을 구분합니다.

## 시작하기 전에

[frame artifact](../01-visual-model/01-rendering-contract-and-frame.md), [pipeline 계약](16-shaders-pipelines-and-render-passes.md), [frame lifecycle](17-frame-lifecycle-synchronization-and-resize.md)을 사용합니다. validation layer나 capture tool은 올바른 이미지까지 보장하지 않으며, API 계약 위반과 의미 오류를 다른 증거로 조사합니다.

### 재현 가능한 한 frame 만들기

그래픽스 문제는 camera·animation·random·asset streaming 때문에 재현이 어렵습니다. 조사 모드에서 다음을 고정합니다.

- scene와 asset generation
- camera pose와 projection
- animation time/tick
- output extent와 format
- backend와 shader artifact hash
- draw order와 random seed
- capture할 frame id

문제가 나타난 frame의 입력을 serialize할 수 있다면 실시간 UI를 다시 조작하는 비용이 줄어듭니다.

### validation message

validation/debug 기능은 다음 문제를 찾는 데 유용합니다.

- invalid 또는 누락 handle
- usage/format/attachment 불일치
- out-of-range binding과 copy
- 잘못된 command/pass 순서
- resource가 아직 사용 중인데 파괴됨
- shader/pipeline interface 일부 오류

각 message에 frame·pass·resource label을 붙입니다. 숫자 handle만 있으면 application state와 연결하기 어렵습니다.

warning을 모두 무시하거나 모두 fatal로 만들지 않습니다. severity와 known baseline을 관리하되, 새 warning은 원인과 영향이 설명되기 전 suppress하지 않습니다.

### debug label과 marker

다음 계층에 사람이 읽을 수 있는 label을 붙입니다.

```text
frame 42
  upload-pass
    mesh:helmet#gen3
  geometry-pass
    pipeline:opaque-textured
    draw:node17/primitive2
  transparent-pass
  present
```

CPU 로그와 frame capture가 같은 이름을 사용하면 draw와 asset을 역추적할 수 있습니다. label 생성이 production 성능에 영향을 주면 debug/profile build에서 활성화합니다.

### frame capture 조사 순서

1. 기대한 frame과 swapchain image를 캡처했는가
2. event 목록에 pass와 draw가 존재하는가
3. render target/depth attachment와 clear/load/store가 맞는가
4. pipeline state, viewport, scissor, culling, depth, blend가 맞는가
5. vertex/index buffer와 offset·format이 맞는가
6. shader, entry point와 binding resource가 맞는가
7. vertex shader input/output이 유효한가
8. fragment input, sampled texture와 output이 유효한가
9. depth/blend 뒤 attachment 값이 어떻게 바뀌었는가
10. present한 image가 조사한 attachment인가

최종 texture viewer만 보지 않고 첫 draw와 작은 marker primitive부터 확인합니다.

### 검은 화면의 decision tree

```text
validation fatal?
├─ yes → 첫 fatal과 resource label 조사
└─ no
   draw count 0?
   ├─ yes → scene/culling/recording
   └─ no
      vertex output clip volume 안?
      ├─ no → transform/projection/layout
      └─ yes
         raster state가 제거?
         ├─ yes → winding/cull/scissor/depth
         └─ no
            fragment output 유효?
            ├─ no → binding/shader/format
            └─ yes → blend/write mask/attachment/present
```

각 분기는 capture나 artifact로 답해야 합니다.

### corruption과 깜빡임

단일 frame이 아니라 수명·동기화 문제일 가능성이 있습니다. 다음 값을 frame별로 비교합니다.

- frame slot과 submission/completion id
- resource generation과 last-use
- upload offset과 hash
- swapchain generation/extent
- shader/pipeline generation
- CPU scene version

capture가 실행되면 timing이 바뀌어 문제가 사라질 수 있습니다. validation·extra wait·capture가 race를 가리는지 주의하고, 독립적인 generation trace와 stress fixture를 유지합니다.

### software reference와 GPU 비교

GPU 최종 image가 software reference와 다를 때 단계별로 비교합니다.

- transform/clip vertex trace
- primitive count와 culling
- primitive-id/coverage image
- depth
- UV/normal/debug attachment
- linear color
- final encoded color

coverage와 primitive id가 다르면 color tolerance를 넓히지 않습니다. 먼저 raster convention을 맞춥니다.

### shader printf와 readback

shader debug output, storage buffer 기록 또는 pixel readback은 선택 도구입니다. parallel invocation이 같은 buffer를 쓸 때 ordering과 bounds를 설계해야 합니다. 모든 fragment를 기록하지 말고 선택 primitive/pixel과 atomic counter를 사용합니다. debug instrumentation이 pipeline layout과 성능을 바꿀 수 있음을 기록합니다.

## 버그 보고서 형식

```text
환경: OS, GPU, driver/backend, API/runtime, shader compiler
재현 입력: scene/camera/settings hash와 frame id
증상: 관찰 가능한 결과
마지막 정상 단계: artifact와 값
첫 비정상 단계: capture event/resource/value
validation: 새 message 또는 없음
최소 변경: 문제를 재현하는 최소 scene/state
기대/실제: 정본 image·trace·수치
```

## 흔한 오답

- validation message가 없으므로 코드가 맞다고 판단
- 검은 화면마다 culling/depth를 모두 끄고 그대로 유지
- capture의 마지막 frame이 문제 frame이라고 가정
- texture viewer의 sRGB display 설정을 실제 resource 값과 혼동
- GPU 차이를 모두 tolerance로 허용
- capture가 race를 숨긴 사실을 무시
- driver bug라고 결론 내리기 전에 최소 재현과 API 계약을 확인하지 않음

## 연결 실습

- [`07-frame-debugging`](../../exercises/07-frame-debugging/README.md): 의도적으로 잘못된 pipeline·layout·frame lifetime 사례를 capture checklist로 분류합니다.
- [`08-renderer-capstone`](../../exercises/08-renderer-capstone/README.md): software/GPU 단계별 비교 보고서를 제출합니다.

## 완료 기준

- 고정 frame을 재현하고 validation·CPU trace·capture event를 같은 label로 연결합니다.
- 검은 화면을 draw 존재·vertex·raster·fragment·blend/present 단계로 분해합니다.
- coverage·depth·attribute·color 중 첫 software/GPU 차이를 찾습니다.
- 수명·동기화 문제를 frame slot·generation·submission trace로 조사합니다.
