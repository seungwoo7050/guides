# 버전 기준

확인일: **2026-08-09**

이 표는 이 저장소의 문서뿐 아니라 현재 실행 가능한 C++ reference, 공개 checker와 GPU profile을 다시 만드는 기준입니다. 최소 버전, 이 저장소가 실제로 확인한 버전, 비교 학습에만 사용하는 명세를 구분합니다. 새 버전이 나왔다는 이유만으로 기준을 자동 갱신하지 않습니다.

| 구성요소 | 저장소 계약 | 이번 확인 환경 | 역할과 검증 범위 |
|---|---|---|---|
| Python | **3.10 이상 필수** | 3.12.13 | repository verifier, checker, mutation·workspace 검사와 PPM oracle |
| C++ | **C++20 compiler 필수** | Apple Clang 21.0.0 | starter/reference/workspace와 sanitizer probe |
| CMake | **3.20 이상 필수** | 3.31.6 | `CG_IMPLEMENTATION`, `CG_GPU`, CTest와 generated header 구성 |
| SDL | **SDL 3.4.10 검증 floor** | SDL 3.4.12 호환 실행 | SDL3 GPU API와 macOS Metal/MSL offscreen reference |
| shader source | tracked MSL과 HLSL | `triangle.metal`, `triangle.hlsl` | MSL은 현재 runtime source, HLSL은 offline cross-target source |
| SDL_shadercross | manifest 고정 commit | `e55cf5e31ced6f3d1be5cc6d0c50e99384f9f4ba` | HLSL에서 SPIR-V·DXIL·MSL을 만드는 선택 offline profile |
| Vulkan | Vulkan 1.4.357 specification | runtime 미검증 | 명시적 GPU API의 비교 정본과 후속 프로젝트 |
| WebGPU | W3C Candidate Recommendation Draft, 2026-05-21 계열 | runtime 미검증 | portable GPU API 비교 경로 |
| WGSL | W3C Candidate Recommendation Draft, 2026-06-05 | compiler/runtime 미검증 | WebGPU shader language 비교 경로 |
| RenderDoc | v1.44 release 문서 | capture 미실행 | 지원 backend에서 사람이 수행할 frame capture 예시 |
| glTF | glTF 2.0 specification/registry | 외부 asset loader 미구현 | scene·asset format 비교 프로필 |

SDL 공식 원격의 확인된 release tag는 다음과 같습니다.

- `release-3.4.10`: `8e37db5e797b6167f3a00d697d816a684bd259c7`
- `release-3.4.12`: `f87239e71e42da91ca317a12eefb82cfbf3393eb`

`3.4.10`은 CMake가 요구하는 stable compatibility floor입니다. `3.4.12`는 이번 호스트에서 `pkg-config`로 확인하고 reference build와 Metal/MSL GPU 경로를 실행한 버전입니다. 후자의 성공이 모든 3.4.x 조합, OS, GPU와 backend 호환성을 일반화하지는 않습니다.

## 필수 도구와 준비 계약

[`prepare.sh`](../prepare.sh)는 `git`, Python 3.10 이상, CMake 3.20 이상과 C++20 compiler를 필수로 검사합니다. package를 설치하거나 source를 수정하지 않습니다. SDL3와 capture 도구는 환경 정보에 기록되는 선택 도구이며, 실제 GPU 평가를 요구할지는 `CG_GPU`/`VERIFY_GPU` mode가 결정합니다.

| CMake `CG_GPU` | configure와 실행 계약 |
|---|---|
| `off` | SDL 검색과 실제 GPU code path를 끕니다. CPU reference와 lifecycle simulator만 평가합니다. |
| `auto` | SDL 3.4.10 이상을 찾으면 GPU code를 빌드합니다. package·device·Metal/MSL 지원이 없으면 GPU 평가는 명시적으로 미실행될 수 있습니다. |
| `required` | SDL 3.4.10 이상을 찾지 못하면 configure가 실패합니다. build 성공 뒤에도 실제 GPU stage가 성공해야 완료 근거로 사용할 수 있습니다. |

`auto`의 미실행은 성공한 GPU 검사가 아닙니다. `off`는 CPU 경로를 재현하기 위한 명시적 선택이며 GPU 종료 능력을 증명하지 않습니다.

## shader 판본과 생성물

현재 runtime은 [`triangle.metal`](../exercises/08-renderer-capstone/project/shaders/triangle.metal)을 CMake configure 단계에서 generated header에 포함하고 SDL Metal device에 MSL source로 전달합니다. [`triangle.hlsl`](../exercises/08-renderer-capstone/project/shaders/triangle.hlsl)은 portable offline 입력입니다.

compiler commit, entry point, vertex layout, source hash와 SPIR-V·DXIL·MSL 생성 명령의 정본은 [`shaders/manifest.json`](../exercises/08-renderer-capstone/project/shaders/manifest.json)입니다. 생성한 `.spv`, `.dxil`, `.msl`/`.metallib`은 `build/` 아래에만 두고 source로 커밋하지 않습니다. 기본 reference build는 `SDL_shadercross`를 요구하지 않습니다.

## 실제 GPU 근거의 범위

현재 SDL GPU reference는 macOS Metal backend에서 추적된 MSL source로 offscreen color/depth frame을 그리고 readback과 fence completion을 검사합니다. 같은 device의 별도 probe는 2 slots·3 submits·12 events, zero-target skip, 64×64→96×72 generation 생성, completion 뒤 slot 재사용·gen1 retire·gen2 readback/retire를 실제 실행합니다. debug/validation 요청, resource·pipeline manifest와 결과 artifact를 남기지만 다음은 자동으로 증명하지 않습니다.

- texture·sampler·material·normal·lighting의 GPU shader/binding parity
- window와 swapchain resize/minimize/restore
- RenderDoc·Xcode·PIX frame capture의 실제 label 대응
- Vulkan·D3D12나 두 번째 SDL backend의 runtime 호환성
- 장시간 여러 frame의 race·driver 안정성
- 설명의 기술적 충분성과 교육적 완료

artifact의 `submit_to_fence_ns`는 CPU의 submit 직전부터 fence wait 완료까지 잰 wall time입니다. queue wait와 CPU scheduling을 포함할 수 있으며 GPU timestamp나 GPU pass duration이 아닙니다.

## 업데이트 시 확인

1. 공식 release tag, header와 API ownership 변화를 확인합니다.
2. Python/C++/CMake 최소 버전 probe와 새 환경 값을 분리해 기록합니다.
3. [`shaders/manifest.json`](../exercises/08-renderer-capstone/project/shaders/manifest.json)의 source hash, compiler commit, target과 명령을 함께 검토합니다.
4. CPU fixture, starter negative control, reference, known-bad mutation, PPM diff와 sanitizer를 다시 실행합니다.
5. 지원 GPU에서는 실제 offscreen GPU path와 validation artifact를 실행합니다.
6. capture, window resize와 다른 backend처럼 자동 범위 밖인 항목은 사람 검토 결과를 별도로 남깁니다.
