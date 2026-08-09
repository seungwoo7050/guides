# 버전 기준

확인일: **2026-08-09**

이 표는 문서 작성 당시 공식 자료를 확인한 기준입니다. 후속 구현은 정확한 tag/header/toolchain을 고정하고, 최신이라는 이유만으로 자동 갱신하지 않습니다.

| 구성요소 | 확인 기준 | 과정에서의 역할 |
|---|---|---|
| C++ | C++20 | CPU 정본과 renderer 구현 언어 |
| CMake | 최소 3.20 권장, 공식 최신 계열 확인 시 4.4 | 후속 구현 build profile |
| SDL | SDL 3.4.10 release 및 SDL3 GPU API 문서 | 권장 cross-platform GPU profile |
| Vulkan | Vulkan 1.4.357 specification | 명시적 GPU API의 세부 정본과 후속 학습 |
| WebGPU | W3C Candidate Recommendation Draft, 2026-05-21 계열 | portable GPU API 비교 경로 |
| WGSL | W3C Candidate Recommendation Draft, 2026-06-05 | WebGPU shader language 비교 경로 |
| RenderDoc | v1.44 release | 지원 backend의 frame capture 예시 |
| glTF | glTF 2.0 공식 specification/registry | scene·asset 구현 프로필 |
| Python | 3.10 이상 | 저장소 검증기와 PPM 도구 |

## 지원 계약

이 압축파일의 `prepare.sh`와 `verify.sh`는 Python 3.10 이상만 필수로 요구합니다. C++ compiler, CMake, SDL3와 RenderDoc은 문서 이후 구현 환경의 선택 도구이며 설치되지 않았다는 이유로 문서 가이드 검증을 실패시키지 않습니다.

후속 renderer 저장소에서는 다음을 별도 고정해야 합니다.

```text
C++ compiler와 표준 라이브러리
CMake exact/minimum version
SDL exact tag와 package 방식
shader compiler·version·options
backend별 shader target
OS·GPU·driver
validation/capture tool
```

## 업데이트 시 확인

- SDL GPU API의 함수와 ownership 계약
- shader format과 binding layout
- swapchain acquire/submit/release 규칙
- Vulkan/WebGPU/WGSL specification 상태와 coordinate/format 규칙
- RenderDoc의 지원 API·platform
- CMake package target과 preset 동작

버전을 바꾼 뒤 CPU fixture, GPU smoke, validation baseline과 known-bad mutation을 다시 실행합니다.
