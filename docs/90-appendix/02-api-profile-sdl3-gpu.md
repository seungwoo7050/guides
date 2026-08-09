# SDL3 GPU 구현 프로필

## 목적

이 문서는 GPU 과정의 개념을 SDL3 GPU API에 옮길 때의 mapping과 조사 순서를 제공합니다. API reference를 복제하지 않으며, 정확한 함수 signature와 지원 조건은 사용하는 SDL3 버전의 공식 문서를 우선합니다.

공식 진입점:

- [SDL3 GPU API category](https://wiki.libsdl.org/SDL3/CategoryGPU)
- [SDL3 API index](https://wiki.libsdl.org/SDL3/FrontPage)
- [SDL_shadercross](https://github.com/libsdl-org/SDL_shadercross)

## 선택 이유와 한계

SDL3 GPU API는 Vulkan·Metal·Direct3D 12 계열의 명시적 resource·pipeline·command 모델을 cross-platform interface로 제공합니다. 첫 renderer에서 window, backend boilerplate와 platform 분기를 줄이면서 현대 GPU 실행 경계를 관찰하기 좋습니다.

한계:

- 모든 저수준 barrier/layout을 직접 노출하지 않습니다.
- backend별 shader format을 준비해야 합니다.
- cutting-edge ray tracing·mesh shader 같은 기능을 목표로 하지 않습니다.
- abstraction이 좌표·format·binding·lifetime 검증을 모두 대신하지 않습니다.

저수준 Vulkan 학습이 목표라면 이 가이드의 CPU 정본과 GPU 상태 모델을 완료한 뒤 별도 Vulkan 프로젝트로 이동합니다.

## 개념 mapping

| 과정 개념 | SDL3 GPU 예 |
|---|---|
| device | `SDL_CreateGPUDevice` 계열 |
| window 연결 | `SDL_ClaimWindowForGPUDevice` |
| command buffer | `SDL_AcquireGPUCommandBuffer` |
| swapchain texture | `SDL_WaitAndAcquireGPUSwapchainTexture` 등 현재 API |
| buffer | `SDL_CreateGPUBuffer` |
| texture | `SDL_CreateGPUTexture` |
| sampler | `SDL_CreateGPUSampler` |
| shader | `SDL_CreateGPUShader` |
| graphics pipeline | `SDL_CreateGPUGraphicsPipeline` |
| copy pass | `SDL_BeginGPUCopyPass` 계열 |
| render pass | `SDL_BeginGPURenderPass` |
| binding | `SDL_BindGPU*` 계열 |
| draw | `SDL_DrawGPUPrimitives`, indexed variant |
| submit | `SDL_SubmitGPUCommandBuffer` 계열 |

함수 이름은 문서 확인 시점의 개념 mapping입니다. release별 추가 variant와 ownership 규칙은 header와 wiki를 확인합니다.

## 기본 초기화 순서

```text
SDL 초기화
→ window 생성
→ 제공 가능한 shader format으로 GPU device 생성
→ window를 device에 claim
→ 선택 driver/backend와 format 기록
→ static resource와 pipeline 생성
→ frame loop
```

실패 단계마다 `SDL_GetError()` 등 현재 오류 API의 메시지를 저장하고 null handle을 다음 단계로 넘기지 않습니다.

## 좌표 규약

SDL3 GPU 공식 문서는 left-handed coordinate system, NDC x/y `[-1,1]`, z `[0,1]`, viewport top-left와 `+Y down`, texture top-left와 `+Y down` 규약을 설명합니다. backend 차이는 SDL이 처리합니다.

과정 규약은 이에 맞춰 CPU 정본을 구성합니다. 그러나 front-face와 projection matrix가 실제 pipeline state와 일치하는지는 marker fixture로 다시 확인합니다. 다른 API/profile로 이동할 때는 입구 변환표를 작성합니다.

## shader format

SDL3 GPU device는 애플리케이션이 제공할 수 있는 shader format을 바탕으로 backend를 선택합니다. 따라서 build에서 다음 matrix를 관리합니다.

```text
source shader
├── SPIR-V target
├── DXIL target
└── Metal-compatible target/MSL/metallib profile
```

실제 지원 format은 사용하는 SDL header와 platform을 확인합니다. runtime cross-compilation을 사용할 수 있지만 배포와 재현성을 위해 offline artifact를 기본으로 권장합니다.

shader manifest:

```json
{
  "source_sha256": "...",
  "compiler": "name version",
  "stage": "vertex",
  "entry_point": "main",
  "format": "spirv",
  "bindings": [],
  "binary_sha256": "..."
}
```

SDL3 GPU resource binding layout은 shader format/backend 규칙과 맞아야 합니다. manual slot count를 작성한다면 reflection과 비교합니다.

## upload

개념적 흐름:

```text
CPU bytes
→ transfer buffer
→ copy pass에서 GPU buffer/texture로 upload
→ copy pass 종료
→ 같은 command buffer 또는 명시된 ordering 뒤 render pass
→ submit
→ completion 뒤 transfer resource 재사용/파괴
```

SDL의 transfer buffer mapping, upload 함수, cycle/overwrite option의 정확한 의미는 현재 API reference에서 확인합니다. “cycle을 요청했으니 무조건 안전하다”는 식으로 추측하지 않고 frame slot과 실제 contract를 기록합니다.

## 한 frame

```text
command buffer 획득
→ swapchain texture 획득
→ 필요한 copy pass
→ depth/offscreen attachment 준비
→ render pass begin(clear/load/store)
→ pipeline/viewport/buffer/texture bind
→ draw
→ render pass end
→ optional readback copy
→ command buffer submit
→ frame slot completion 추적
```

swapchain texture를 얻지 못했을 때 zero extent/minimize와 fatal error를 구분합니다. acquired texture handle을 다음 frame까지 보관하지 않습니다.

## resize와 release

새 drawable extent에서 depth/offscreen attachment를 새로 생성하고 이전 generation은 last-use completion 뒤 release합니다. window-device 연결 해제와 device/resource release 순서는 현재 SDL API 문서에 맞추되, 논리 순서는 [frame lifecycle](../04-gpu-rendering/17-frame-lifecycle-synchronization-and-resize.md)을 유지합니다.

## debug와 capture

- 모든 resource와 pass에 가능한 debug name/label을 사용합니다.
- SDL validation/debug property가 있다면 device 생성 전 명시합니다.
- backend가 RenderDoc을 지원하는 환경에서는 한 frame을 capture합니다.
- Metal/Xcode, D3D12/PIX 같은 platform tool로 이동할 때 같은 frame id와 resource label을 사용합니다.

RenderDoc이나 validation이 SDL abstraction 내부까지 어떻게 보이는지는 backend와 build에 따라 다를 수 있습니다. tool이 없거나 capture할 수 없는 환경을 renderer correctness 실패와 구분합니다.

## 최소 build profile

실제 후속 구현 저장소에서 다음을 고정합니다.

- SDL3 정확한 version/tag
- CMake가 찾는 package 방식과 target 이름
- shader compiler와 target format
- platform별 runtime/library 배치
- debug/validation toggle
- 지원 OS/GPU/backend matrix

이 압축파일의 자동 검증은 SDL3 설치를 요구하지 않습니다. 문서와 계약을 platform-independent하게 유지하기 위해서입니다.

## API를 바꿀 때 유지할 것

Vulkan, WebGPU, Metal 또는 D3D12로 옮겨도 다음 정본은 유지합니다.

- coordinate/color/alpha/sample 규약
- scene와 frame input
- software fixture
- resource descriptor와 generation
- shader/pipeline manifest
- frame slot과 completion
- validation/capture 조사 순서
- CPU/GPU timing과 image 비교 보고서
