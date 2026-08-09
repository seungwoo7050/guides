# 버전 기준과 플랫폼 노트

## 목적

그래픽스 API, shader language, driver와 capture tool은 계속 바뀝니다. 문서의 개념 계약과 특정 버전의 함수·format·지원 상태를 분리하고, 후속 구현이 재현 가능한 환경 기준을 남기도록 합니다.

정확한 확인일과 공식 출처는 [`reference/version-baseline.md`](../../reference/version-baseline.md)에 있습니다.

## 고정되는 것과 바뀌는 것

### 과정이 고정하는 것

- coordinate/color/alpha/sample 규약
- software fixture와 artifact 의미
- resource·pipeline·frame lifecycle의 상태 경계
- validation/capture 조사 순서
- correctness와 performance 근거의 분리

### 구현마다 기록할 것

- OS와 architecture
- GPU와 driver
- SDL3 또는 다른 API/runtime version
- backend와 shader format
- C++ compiler와 CMake
- shader compiler/options
- RenderDoc/PIX/Xcode 등의 tool version
- build type와 validation 설정

문서가 최신 API 이름을 포함하더라도 실제 header를 정본으로 사용합니다.

## Linux

가능한 backend와 driver stack이 여러 가지입니다. 다음을 기록합니다.

- distribution과 kernel
- display server/session 관련 정보가 필요한 경우
- GPU vendor/model과 driver package
- Vulkan loader/ICD가 선택한 device
- validation layer와 capture tool의 설치 여부

software renderer나 headless CI는 GPU backend가 없어도 문서·CPU fixture를 검증할 수 있어야 합니다. GPU test는 지원 환경에서 별도 job으로 분리합니다.

## Windows

D3D12와 Vulkan backend, shader target과 debug tool이 다를 수 있습니다. DLL/runtime 배치와 graphics tools optional feature를 문서화합니다. debug layer가 없는 환경을 코드 오류로 보고하지 않되 release renderer smoke와 분리합니다.

## macOS

Metal backend와 Apple platform shader artifact를 준비합니다. window drawable scale과 logical size를 구분하고, capture는 Xcode GPU tool 또는 지원되는 다른 경로를 사용합니다. Vulkan 경로는 portability layer를 사용하는 경우 그 layer/version을 별도 기록합니다.

## WSL·VM·원격 환경

GPU forwarding과 window/capture 지원이 제한될 수 있습니다. CPU software track과 문서 검증은 실행 가능하게 유지하고, GPU track의 SKIP 이유를 명시합니다. “CI에서 안 되므로 GPU 코드가 맞다/틀리다”로 판단하지 않습니다.

## high-DPI

window logical size와 drawable pixel extent를 구분합니다. screenshot, viewport, mouse picking과 UI coordinate가 어느 단위를 사용하는지 기록합니다. resize fixture에는 scale factor 변화도 포함할 수 있습니다.

## shader portability

하나의 source language에서 여러 target을 만들더라도 compiler와 backend의 다음 차이를 확인합니다.

- resource binding mapping
- matrix/layout와 alignment
- available feature와 limit
- precision·fast math
- coordinate/depth convention
- entry point와 binary format

cross-compiler가 성공했다고 runtime interface가 맞는 것은 아닙니다. reflection manifest와 marker fixture를 유지합니다.

## CI matrix

최소 matrix:

```text
all jobs
- 문서·link·contract 검증
- PPM diff self-test
- CPU software fixture

지원 job
- Linux 또는 Windows GPU smoke
- validation enabled
- fixed scene screenshot/readback

선택 job
- 두 번째 backend/platform
- frame capture artifact
- performance trend (pass/fail보다 report 중심)
```

성능 숫자를 서로 다른 runner에서 단일 threshold로 비교하지 않습니다. correctness와 environment 기록을 우선합니다.

## 업데이트 절차

1. 공식 release notes와 header/spec를 확인합니다.
2. 버전 기준 문서의 확인일과 값만 먼저 갱신하지 않습니다.
3. build·shader·runtime smoke를 새 version에서 실행합니다.
4. API/format/coordinate 변화가 과정 계약에 미치는 영향을 기록합니다.
5. known-bad mutation과 reference image 검사를 다시 실행합니다.
6. 이전 지원 version을 제거한다면 migration 경로와 이유를 남깁니다.
