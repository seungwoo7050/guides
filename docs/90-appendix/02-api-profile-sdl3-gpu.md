# SDL3 GPU 구현 프로필

## 목적

이 문서는 현재 누적 C++20 project가 GPU 과정의 resource·pipeline·command·completion 계약을 SDL3 GPU API에 어떻게 옮기는지 설명합니다. API reference를 복제하지 않으며 함수 signature와 지원 조건은 사용하는 SDL3 header와 공식 문서를 우선합니다.

공식 진입점:

- [SDL3 GPU API category](https://wiki.libsdl.org/SDL3/CategoryGPU)
- [SDL3 API index](https://wiki.libsdl.org/SDL3/FrontPage)
- [SDL_shadercross](https://github.com/libsdl-org/SDL_shadercross)
- [이 저장소의 버전 기준](../../reference/version-baseline.md)

## 현재 지원 기준

Python 3.10 이상, C++20 compiler와 CMake 3.20 이상은 저장소 전체의 필수 도구입니다. SDL3 GPU code의 stable compatibility floor는 SDL **3.4.10**이며, 이번 macOS 환경에서는 SDL **3.4.12**로 build와 Metal/MSL offscreen 실행을 확인했습니다.

| CMake 설정 | 의미 |
|---|---|
| `CG_GPU=off` | SDL을 찾지 않고 CPU renderer와 lifecycle simulator만 빌드·검사합니다. |
| `CG_GPU=auto` | SDL 3.4.10 이상을 찾으면 GPU code를 포함합니다. package나 runtime device가 없으면 실제 GPU stage는 미평가로 남을 수 있습니다. |
| `CG_GPU=required` | SDL을 찾지 못하면 configure가 실패하며, 실제 GPU stage가 실행되지 않으면 GPU 검증 성공으로 보고할 수 없습니다. |

`off`와 `auto`에서 GPU를 실행하지 않은 결과는 “GPU path 통과”가 아닙니다. 실제 GPU 근거가 필요하면 지원 host에서 `required`를 사용하고 생성된 `environment.json`, validation log와 readback artifact를 보존합니다.

## 선택 이유와 한계

SDL3 GPU API는 Vulkan·Metal·Direct3D 12 계열의 명시적 resource·pipeline·command 모델을 cross-platform interface로 제공합니다. window/backend boilerplate를 줄이면서 resource lifetime과 비동기 completion을 관찰하기 좋습니다.

다만 현재 reference의 실제 장치 경로는 **macOS Metal + MSL source + offscreen target**으로 제한됩니다.

- 모든 저수준 barrier와 layout을 직접 노출하지 않습니다.
- 실제 Vulkan·D3D12 backend는 이 저장소에서 실행하지 않았습니다.
- window/swapchain을 만들지 않으므로 실제 resize·minimize·drawable scale을 검증하지 않습니다.
- debug/validation device를 요청하지만 외부 validation layer의 모든 메시지를 포착한다는 보장은 없습니다.
- capture tool을 내장하지 않으며 Xcode·RenderDoc·PIX capture는 사람 검토 항목입니다.
- ray tracing·mesh shader와 GPU compiler/driver 개발은 범위 밖입니다.

## 개념 mapping

| 과정 개념 | SDL3 GPU 예 |
|---|---|
| device | `SDL_CreateGPUDevice` |
| window 연결 | `SDL_ClaimWindowForGPUDevice` — 현재 offscreen reference에서는 미사용 |
| command buffer | `SDL_AcquireGPUCommandBuffer` |
| swapchain texture | `SDL_WaitAndAcquireGPUSwapchainTexture` — 현재 실제 경로에서는 미사용 |
| buffer | `SDL_CreateGPUBuffer` |
| texture | `SDL_CreateGPUTexture` |
| sampler | `SDL_CreateGPUSampler` |
| shader | `SDL_CreateGPUShader` |
| graphics pipeline | `SDL_CreateGPUGraphicsPipeline` |
| copy pass | `SDL_BeginGPUCopyPass` |
| render pass | `SDL_BeginGPURenderPass` |
| binding | `SDL_BindGPU*` 계열 |
| draw | `SDL_DrawGPUIndexedPrimitives` |
| submit·completion | `SDL_SubmitGPUCommandBufferAndAcquireFence`, `SDL_WaitForGPUFences` |

함수 이름은 SDL 3.4.10 floor에서 확인한 mapping입니다. release를 바꾸면 header, ownership, error path와 생성·해제 순서를 다시 검사합니다.

## 현재 실제 frame 경로

[`reference/gpu.cpp`](../../exercises/08-renderer-capstone/project/reference/gpu.cpp)의 실제 GPU 경로는 다음 순서를 수행합니다.

```text
SDL video 초기화
→ Metal/MSL 지원 확인과 debug GPU device 생성
→ offscreen RGBA8 color·D16 depth target 생성
→ vertex/index/upload/download resource 생성
→ tracked MSL vertex·fragment shader와 pipeline 생성
→ upload copy pass
→ indexed triangle color/depth render pass
→ color/depth readback copy pass
→ submit + fence 획득
→ fence completion 대기
→ readback과 artifact 기록
→ 역순 release
```

null handle, 지원하지 않는 target format과 fence wait 실패는 명시적으로 거부합니다. lifecycle simulator가 만드는 resize generation trace는 resource 상태 기계의 결정적 oracle이지만 실제 window resize event나 swapchain 재생성을 실행한 증거는 아닙니다.

stage 06과 08의 actual lifecycle probe는 위 baseline draw와 별도로 **하나의 같은 Metal device**를 유지하며 다음 사건을 실행합니다.

```text
64×64 generation 1 생성
→ slot 0 submission 1, slot 1 submission 2
→ zero extent target 생성 생략
→ submission 1 completion 뒤 slot 0 재사용 가능
→ 96×72 generation 2 생성, slot 0 submission 3
→ submission 2 completion 뒤 generation 1 retire
→ submission 3 completion 뒤 generation 2 color/depth readback
→ generation 2 retire
```

artifact는 이 순서를 2 slots·3 submits·12 events로 기록하고 결정적 lifecycle model과 대조합니다. 두 extent에서 실제 offscreen texture를 생성하고 새 generation을 readback하지만 window를 claim하거나 swapchain을 acquire하지 않으므로, 실제 resize·minimize·restore·high-DPI 증거로 확대 해석하지 않습니다.

## shader source와 manifest

현재 source 역할은 분명히 나뉩니다.

- [`triangle.metal`](../../exercises/08-renderer-capstone/project/shaders/triangle.metal): **실제 macOS runtime source**. CMake가 source를 읽어 build directory의 generated header에 포함하고 `SDL_GPU_SHADERFORMAT_MSL`로 device에 전달합니다.
- [`triangle.hlsl`](../../exercises/08-renderer-capstone/project/shaders/triangle.hlsl): SPIR-V·DXIL·MSL을 만들기 위한 **offline portable source**. 기본 build와 Metal runtime은 이 파일을 compile하지 않습니다.

compiler commit, source 역할, entry point, vertex layout, tracked MSL hash와 offline 명령의 정본은 [`shaders/manifest.json`](../../exercises/08-renderer-capstone/project/shaders/manifest.json)입니다. 현재 SDL_shadercross 고정 commit은 `e55cf5e31ced6f3d1be5cc6d0c50e99384f9f4ba`입니다.

manifest의 명령은 HLSL에서 다음 target을 만듭니다.

```text
vertex_main / fragment_main
├── SPIR-V: build/shaders/*.spv
├── DXIL:   build/shaders/*.dxil
└── MSL:    build/shaders/*.msl
```

명령을 문서에 따로 복제해 drift시키지 않고 manifest를 실행 정본으로 사용합니다. 생성된 `.spv`, `.dxil`, `.msl`과 선택적으로 만든 `.metallib`은 `build/` 아래에만 두며 Git source로 추가하지 않습니다. compiler·options·input hash·output hash를 결과 manifest에 기록한 뒤 사용합니다.

## 좌표와 interface 계약

과정 정본은 column vector, `clip = P * V * M * local`, left-handed `+Z` camera, NDC depth `[0,1]`, top-left viewport와 linear RGB 연산을 사용합니다. SDL abstraction이 backend 차이를 처리하더라도 다음은 marker fixture와 readback으로 다시 확인합니다.

- vertex attribute location, stride와 offset
- shader entry point와 source format
- color/depth attachment format과 pipeline target
- front-face, culling과 depth compare
- output channel·encoding과 alpha 의미

offline cross-compilation 성공만으로 runtime interface가 맞다고 판단하지 않습니다. reflection 또는 명시적 manifest를 CPU-side vertex layout과 비교합니다.

## upload, submit과 측정

upload resource는 copy completion까지 살아 있어야 하고, download buffer는 fence completion 뒤에만 map합니다. 현재 reference가 기록하는 `submit_to_fence_ns`는 다음 구간의 **CPU wall time**입니다.

```text
submit 직전의 steady clock
→ command buffer submit
→ CPU의 fence wait 반환
```

이 값에는 queue 대기와 CPU scheduling이 섞일 수 있습니다. GPU timestamp query가 아니며 shader, render pass 또는 GPU 전체 실행 시간으로 해석하면 안 됩니다. 실제 GPU 병목 분석에는 backend가 제공하는 timestamp와 capture/profile tool을 별도로 사용합니다.

## validation과 capture

실제 GPU path는 debug/validation을 요청하고 fatal·warning baseline, environment, shader/resource/pipeline/frame trace를 남깁니다. 이는 다음을 구분하는 근거입니다.

- SDL/API가 보고한 생성·submit 오류
- readback/image oracle이 찾는 semantic 오류
- lifecycle simulator가 찾는 generation·completion 오류

하지만 자동 검증은 실제 capture file을 만들거나 capture label이 외부 도구에 정확히 보이는지 확인하지 않습니다. Xcode GPU capture, 지원되는 RenderDoc backend 또는 PIX에서 같은 frame/label을 사람이 확인하고 tool version·driver·capture 영향을 기록합니다.

## API나 platform을 바꿀 때 유지할 것

Vulkan, WebGPU, Metal 또는 D3D12로 옮겨도 다음 정본은 유지합니다.

- coordinate/color/alpha/sample 규약
- repository-generated scene와 frame input
- software fixture와 단계별 artifact
- resource descriptor, generation과 completion
- shader/pipeline manifest
- validation/capture 조사 순서
- CPU wall time, GPU timestamp와 image correctness의 구분

다른 backend에서 runtime을 추가하면 해당 binary/source format, device, validation과 readback 결과를 새 근거로 남깁니다. 현재 Metal/MSL 성공을 다른 backend 성공으로 재사용하지 않습니다.
