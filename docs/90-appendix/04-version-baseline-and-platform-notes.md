# 버전 기준과 플랫폼 노트

## 목적

그래픽스 API, shader compiler, driver와 capture tool은 계속 바뀝니다. 이 문서는 과정의 불변 계약, 현재 저장소가 실제 실행한 환경과 아직 실행하지 않은 platform을 구분합니다. 정확한 판본과 공식 tag는 [`reference/version-baseline.md`](../../reference/version-baseline.md), shader compiler와 명령은 [`shaders/manifest.json`](../../exercises/08-renderer-capstone/project/shaders/manifest.json)이 정본입니다.

## 필수 기반과 현재 확인 환경

모든 지원 환경은 다음 기반을 먼저 만족해야 합니다.

- Python 3.10 이상
- C++20 compiler
- CMake 3.20 이상

이번 확인 환경은 Python 3.12.13, Apple Clang 21.0.0, CMake 3.31.6, SDL 3.4.12입니다. SDL 3.4.10은 CMake compatibility floor이고 3.4.12는 실제 macOS Metal/MSL offscreen 경로를 실행한 판본입니다. 한 host의 성공은 다른 OS, GPU, driver 또는 SDL backend의 성공을 뜻하지 않습니다.

## 고정되는 것과 환경마다 기록할 것

### 과정이 고정하는 것

- coordinate/color/alpha/sample 규약
- repository-generated software fixture와 artifact 의미
- resource·pipeline·frame lifecycle의 상태 경계
- validation·semantic oracle·capture 조사 순서
- correctness, CPU wall time와 GPU timestamp의 구분

### 실행마다 기록할 것

- OS, architecture와 display/window 환경
- GPU, driver와 선택된 SDL backend
- SDL runtime/header version과 `CG_GPU` mode
- C++ compiler, standard library와 CMake
- shader source, compiler commit/options, entry point와 output hash
- validation/debug 설정
- RenderDoc·PIX·Xcode 등 capture tool과 실제 capture 여부
- build type, sanitizer와 CPU/GPU timing 방식

문서의 API 이름보다 실제 header와 생성 artifact를 우선합니다.

## `CG_GPU`와 검증 해석

| mode | 구성 결과 | 결과 해석 |
|---|---|---|
| `off` | SDL 검색을 생략하고 CPU·lifecycle simulator를 실행 | GPU 종료 능력은 평가하지 않음 |
| `auto` | SDL 3.4.10 이상이 있으면 GPU code를 구성 | package/device/backend가 없으면 GPU가 명시적으로 미평가될 수 있음 |
| `required` | SDL을 찾지 못하면 configure 실패 | 실제 GPU stage까지 통과해야 GPU 근거로 인정 |

`VERIFY_GPU`는 repository 검증이 CMake와 checker에 전달하는 같은 정책입니다. `VERIFY_STRICT=1`은 `auto`를 허용하지 않으므로 `required` 또는 `off`를 명시해야 합니다. `off`를 명시한 strict 검증도 GPU를 통과시킨 것이 아니라 GPU 비평가 결정을 명확히 한 것입니다.

## macOS — 현재 실제 GPU profile

현재 reference는 macOS에서 Metal driver와 tracked MSL source를 사용해 offscreen RGBA8 color·D16 depth frame을 실행합니다. vertex/index upload, pipeline, indexed draw, color/depth readback, submit과 fence completion에 더해, 같은 device에서 2 slots·3 submits로 64×64→96×72 offscreen generation을 실제 생성하고 completion 뒤 slot 재사용·이전 generation retire·새 generation readback을 검사합니다. zero extent에서는 target을 만들지 않으며 전체 실제 사건은 12개로 기록됩니다.

현재 자동 범위에 포함되지 않는 항목:

- window와 swapchain 생성
- resize·minimize·restore와 high-DPI drawable 변화
- Xcode GPU capture의 실제 file과 label 확인
- 장시간 여러 frame·device-loss stress
- Vulkan portability layer 경로

`submit_to_fence_ns`는 CPU가 submit 직전부터 fence wait 반환까지 잰 wall time이며 Metal GPU timestamp가 아닙니다.

## Linux

CPU software와 lifecycle simulator는 window/GPU 없이 실행할 수 있습니다. 실제 GPU 지원을 주장하려면 다음을 별도 기록하고 실행합니다.

- distribution, kernel, display/session
- GPU vendor/model, driver package와 Vulkan loader/ICD
- SDL이 선택한 backend와 shader format
- validation layer와 capture tool
- offscreen/readback 또는 window/swapchain 결과

tracked HLSL에서 만든 SPIR-V command는 manifest에 있지만, 이 저장소는 Linux Vulkan runtime을 실행하지 않았습니다. offline compile 성공만으로 Linux GPU 호환을 표시하지 않습니다.

## Windows

D3D12/Vulkan backend, DXIL/SPIR-V target, DLL 배치와 debug tool을 기록합니다. manifest는 DXIL 생성 명령을 제공하지만 현재 reference는 DXIL/D3D12를 runtime에서 소비하지 않습니다. PIX/debug layer가 없는 환경과 코드 오류를 구분하되, 실제 device·pipeline·readback 실행 없이 Windows GPU 지원을 주장하지 않습니다.

## WSL·VM·원격 환경

GPU forwarding, window와 capture 지원이 제한될 수 있습니다. CPU·lifecycle 경로는 실행할 수 있지만 GPU stage가 미평가되면 이유와 mode를 결과에 남깁니다. “CI에서 실행하지 못했다”는 사실은 GPU code의 정답 또는 오답 근거가 아닙니다.

## high-DPI와 resize

window logical size와 drawable pixel extent를 구분해야 합니다. screenshot, viewport, mouse picking과 UI coordinate의 단위를 기록하고 resize fixture에는 scale factor 변화를 포함합니다.

현재 reference의 실제 SDL path는 offscreen 64×64와 96×72 두 extent의 generation 전이를 실행하지만 window/swapchain을 만들지 않습니다. 따라서 high-DPI와 platform window resize를 자동 검증하지 않습니다. 실제 probe와 `resource-events.json`·lifecycle simulator의 zero-extent/generation 결과는 resource 상태 oracle이지 platform window event의 대체 증거가 아닙니다.

## shader portability와 생성물

현재 macOS runtime은 tracked [`triangle.metal`](../../exercises/08-renderer-capstone/project/shaders/triangle.metal)을 직접 사용합니다. tracked [`triangle.hlsl`](../../exercises/08-renderer-capstone/project/shaders/triangle.hlsl)과 SDL_shadercross 고정 commit은 SPIR-V·DXIL·MSL offline profile을 제공합니다.

다음 차이를 target별로 검토합니다.

- resource binding과 vertex layout mapping
- matrix/layout alignment
- feature와 format limit
- precision·fast math
- coordinate/depth convention
- entry point와 binary/source format

generated `.spv`, `.dxil`, `.msl`/`.metallib`은 `build/` 아래에만 두며 추적하지 않습니다. cross-compiler 성공은 runtime interface, validation, readback과 image correctness를 보장하지 않습니다.

## repository 검증 matrix

[`verify.sh`](../../verify.sh)는 원본이 아닌 고유 임시 복사본에서 다음을 실행합니다.

```text
항상
- repository 문서·상대 링크·anchor·contract와 negative controls
- Python syntax와 PPM oracle
- starter not-implemented negative control
- reference stage와 known-bad mutation
- workspace 생성·비파괴 안전 검사
- release build와 CTest

지원되는 compiler/runtime
- address/undefined sanitizer build와 CTest

VERIFY_GPU mode에 따라
- off: CPU·lifecycle만, GPU 미평가
- auto: 지원 시 실제 GPU, 미지원이면 이유와 미평가 표시
- required: SDL configure와 실제 GPU stage 필수
```

이 검증은 존재하는 공개 행동과 artifact의 회귀 근거입니다. 다음을 자동 증명하지 않습니다.

- 문서의 교육적 완성이나 설명 전체의 정확성
- 실제 창 resize/high-DPI 경로
- frame capture file과 외부 tool label
- 실행하지 않은 backend/platform
- 서로 다른 runner 사이의 절대 성능 우열

## 업데이트 절차

1. 공식 release tag, header와 specification을 확인합니다.
2. 최소 floor와 이번 실행 환경을 같은 값으로 섞지 않습니다.
3. tracked shader source와 manifest compiler commit·명령·hash를 함께 검토합니다.
4. CPU reference, starter, mutation, PPM와 sanitizer를 다시 실행합니다.
5. 지원 platform에서는 `CG_GPU=required`로 actual GPU readback까지 실행합니다.
6. window resize, capture와 다른 backend는 별도 사람 검토 근거를 남깁니다.
7. 이전 지원 판본을 제거하면 migration 이유와 알려진 실패를 기록합니다.
