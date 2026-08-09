# 공식 명세와 도구 자료

이 가이드는 개인 기술 글보다 API·format·shader language·tool의 공식 문서를 우선합니다. 링크는 정본의 진입점이며, 실제 구현에서는 확인한 version/tag와 날짜를 함께 기록합니다.

## SDL3 GPU

- [SDL3 GPU API](https://wiki.libsdl.org/SDL3/CategoryGPU): device, shader, buffer, texture, sampler, pipeline, command buffer와 pass의 기본 workflow 및 좌표 규약
- [SDL3 Front Page](https://wiki.libsdl.org/SDL3/FrontPage): 현재 SDL3 API index
- [SDL releases](https://github.com/libsdl-org/SDL/releases): 정확한 release tag와 source/binary artifact
- [SDL_shadercross](https://github.com/libsdl-org/SDL_shadercross): 여러 backend target을 위한 shader cross-compilation 도구
- [SDL GPU examples](https://github.com/TheSpydog/SDL_gpu_examples): 공식 문서가 연결하는 사용 예제 프로젝트

SDL wrapper가 보장하는 것과 backend 자체가 보장하는 것을 구분합니다. function signature와 release별 변경은 설치한 header를 우선합니다.

## Vulkan·SPIR-V

- [Vulkan Registry](https://registry.khronos.org/vulkan/): 최신 specification, reference와 header 진입점
- [Vulkan Specification](https://registry.khronos.org/vulkan/specs/latest/html/vkspec.html): resource, pipeline, synchronization과 API 계약
- [Vulkan Guide](https://docs.vulkan.org/guide/latest/): 공식 사용 지침과 개념 설명
- [Vulkan Synchronization Examples](https://github.com/KhronosGroup/Vulkan-Docs/wiki/Synchronization-Examples): dependency와 barrier 사례
- [SPIR-V Registry](https://registry.khronos.org/SPIR-V/): shader intermediate representation 명세
- [Vulkan Validation Layers](https://github.com/KhronosGroup/Vulkan-ValidationLayers): validation 구현과 issue
- [Vulkan Samples](https://github.com/KhronosGroup/Vulkan-Samples): 공식 sample과 best practice 자료

Vulkan의 세부 synchronization이나 layout을 SDL3가 그대로 노출한다고 가정하지 않습니다. 후속 Vulkan 구현에서만 직접 적용합니다.

## WebGPU와 WGSL

- [WebGPU](https://www.w3.org/TR/webgpu/): W3C API specification
- [WGSL](https://www.w3.org/TR/WGSL/): WebGPU shader language specification
- [GPUWeb specification sources](https://github.com/gpuweb/gpuweb): issue, source와 test 관련 논의

WebGPU/WGSL은 Candidate Recommendation Draft 상태가 갱신될 수 있으므로 확인 날짜와 문서 version을 남깁니다.

## asset와 image format

- [glTF 2.0 repository and specification](https://github.com/KhronosGroup/glTF): scene·mesh·material·extension 정본
- [glTF Validator](https://github.com/KhronosGroup/glTF-Validator): asset validation 도구와 issue
- [glTF Sample Assets](https://github.com/KhronosGroup/glTF-Sample-Assets): importer/viewer fixture 후보; 각 asset의 라이선스를 확인
- [Khronos Data Format Specification](https://registry.khronos.org/DataFormat/): channel, numeric format와 data format description
- [KTX specification](https://registry.khronos.org/KTX/): texture container 후속 학습 자료
- [PNG specification](https://www.w3.org/TR/png-3/): PNG format의 공식 W3C specification

현재 저장소는 외부 image·mesh·scene asset을 포함하지 않습니다. `scene-v1.json`과 `marker-texture.json`은 저장소가 만든 MIT fixture이고, invalid/event JSON도 저장소 test input입니다. 외부 asset을 추가할 때는 source URL·가져온 날짜·content hash·원본 license·재배포 가능 여부와 import profile을 기록하며, 저장소 생성 fixture라고 잘못 표시하지 않습니다. 자세한 조건은 [라이선스](../LICENSE.md)와 [안전 및 운영 계약](../SAFETY.md)을 따릅니다.

## color와 수치

- [IEC sRGB information page](https://www.color.org/chardata/rgb/srgb.xalter): sRGB color space의 공식 정보 진입점
- [ICC specifications](https://www.color.org/icc_specs2.xalter): color management 후속 학습
- [IEEE 754-2019](https://standards.ieee.org/ieee/754/6210/): 부동소수점 표준 정보

전문 color management와 HDR 표준 전체는 이 가이드의 범위 밖입니다.

## debugging과 profiling

- [RenderDoc](https://github.com/baldurk/renderdoc): open-source graphics debugger와 release
- [RenderDoc documentation](https://renderdoc.org/docs/): capture·UI·Python API 사용 자료
- [Microsoft PIX](https://devblogs.microsoft.com/pix/documentation/): D3D12 profiling/debugging
- [Apple Metal developer tools](https://developer.apple.com/metal/tools/): Metal capture와 profiling
- [NVIDIA Nsight Graphics](https://developer.nvidia.com/nsight-graphics): 지원 GPU/API의 frame debugging과 profiling
- [AMD Radeon GPU Profiler](https://gpuopen.com/rgp/): AMD GPU timing과 pipeline 분석

vendor counter는 hardware와 tool version에 따라 의미가 다릅니다. 지원 여부와 환경을 결과에 포함합니다.

## build

- [CMake documentation](https://cmake.org/cmake/help/latest/): CMake command와 target 계약
- [CMake releases](https://cmake.org/cmake/help/latest/release/index.html): release별 변경

## 확인 원칙

1. 공식 specification과 설치한 header를 우선합니다.
2. tutorial의 matrix·coordinate·depth convention을 과정 규약과 대조합니다.
3. sample이 성공해도 lifetime·error·resize·validation 경계를 별도로 검사합니다.
4. 표와 코드 전체를 복제하지 않고 필요한 의미를 자체 설명과 fixture로 만듭니다.
5. version-dependent 내용은 [`version-baseline.md`](version-baseline.md)를 갱신합니다.
