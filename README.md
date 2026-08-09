# 컴퓨터 그래픽스 개발 가이드

이 저장소는 화면에 보이는 결과를 만드는 API 사용법만 나열하지 않습니다. 장면의 값이 좌표 변환·클리핑·래스터화·샘플링·깊이·조명·혼합을 지나 **프레임의 픽셀과 GPU 작업**이 되는 과정을 하나의 상태 모델로 연결합니다.

학습 경로는 두 구현 단계로 나뉩니다.

```text
CPU 소프트웨어 렌더러
    좌표·클리핑·삼각형 coverage·보간·깊이·색·텍스처
    → 픽셀 결과와 중간 산출물을 결정적으로 검증

GPU 렌더러
    resource·shader·pipeline·command buffer·render pass·동기화
    → 같은 장면을 비동기 GPU 실행 모델로 이전하고 측정
```

소프트웨어 렌더러는 실제 제품 렌더러의 성능을 흉내 내기 위한 것이 아닙니다. 그래픽스 API가 대신 수행하는 상태 전이와 픽셀 규칙을 직접 구현해, GPU 단계에서 보이는 검은 화면·뒤집힌 좌표·깨진 깊이·잘못된 blending·resource lifetime 오류를 원리와 증거로 좁힐 수 있게 합니다.

대상 독자, 선행 브랜치, 좌표·색·alpha 규약과 구현 프로필은 [학습 로드맵과 범위 계약](docs/00-roadmap.md)에 있습니다.

## 선행 경로

이 브랜치는 다음 가이드의 결과를 다시 가르치지 않습니다.

- [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp): C++20, 값·수명·RAII, CMake, 테스트와 디버깅
- [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms): 문제 계약, 자료구조, 복잡도, 기준 구현과 반례
- [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture): 데이터 배치, 캐시·SIMD·멀티코어, 성능식과 측정

벡터와 행렬은 그래픽스 좌표 변환에 필요한 범위에서 사용하지만, 일반 선형대수 과정으로 확장하지 않습니다. C++ 문법·RAII·CMake·일반 성능 측정도 필요한 접점만 연결합니다.

## `main` 카탈로그 계약

이 브랜치의 정본은 최신 `main`의 [`catalog/branches.json`](https://github.com/seungwoo7050/guides/blob/main/catalog/branches.json)과 [`catalog/tracks.json`](https://github.com/seungwoo7050/guides/blob/main/catalog/tracks.json)입니다. 카탈로그에서 이 가이드는 `specialization`이며, 목적은 “벡터·행렬·이미지·rasterization·shader·GPU resource·동기화·frame budget을 software renderer와 GPU pipeline으로 연결한다”입니다.

| 관계 | 카탈로그 계약 | 이 가이드에서의 적용 |
|---|---|---|
| `requires` | `cpp`, `algorithms`, `computer-architecture` | C++20 구현, 결정적 fixture·반례, 메모리·성능 측정 능력을 전제로 합니다. |
| `recommends` | `operating-systems` | process·thread·동기화와 driver 경계를 더 깊게 조사할 때 권장하지만 시작을 막지는 않습니다. |
| `connects` | `game-development` | 엔진의 frame·scene·asset 문맥과 그래픽스 pipeline을 잇는 인접 계약입니다. 구현 범위는 이 가이드 안에서 임의로 확장하지 않습니다. |
| `continues_to` | 없음 | 단일 후속 브랜치를 강제하지 않고 목적에 맞는 프로젝트·트랙으로 이동합니다. |

이 브랜치가 소유하는 범위는 다음 다섯 가지입니다.

- 좌표계·camera·projection
- image·color·sampling
- software rasterization
- shader와 GPU pipeline
- resource lifetime·CPU/GPU synchronization·profiling

반대로 C++ 기초, 게임 엔진 전체, 3D 아트 제작, GPU 하드웨어 설계는 소유하지 않습니다. 필요한 전제만 링크하고 이 브랜치의 상태·실패·관측 모델에 적용되는 부분만 깊게 다룹니다.

완료 시에는 다음 세 가지 종료 능력을 실제 artifact와 검사 결과로 입증해야 합니다.

1. 작은 software renderer를 구현합니다.
2. 같은 장면을 GPU pipeline으로 옮깁니다.
3. frame-time과 자원 수명을 측정·진단합니다.

세 종료 능력이 문서·실습·대표 실패·capstone 증거로 연결되는 표는 [로드맵의 계약 추적표](docs/00-roadmap.md#owns에서-종료-능력까지의-추적표)에 있습니다.

## 읽는 순서

### Part 1. 프레임을 정의하는 값과 규약

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 01 | [렌더링 계약과 한 프레임](docs/01-visual-model/01-rendering-contract-and-frame.md) | 장면에서 프레임까지 어떤 입력·상태·산출물을 고정해야 합니까? |
| 02 | [좌표 공간과 변환](docs/01-visual-model/02-coordinate-spaces-and-transforms.md) | local·world·view·clip·NDC·viewport를 어떻게 구분합니까? |
| 03 | [카메라·투영·클리핑](docs/01-visual-model/03-camera-projection-and-clipping.md) | 카메라 밖의 기하를 언제 버리고 언제 잘라야 합니까? |
| 04 | [이미지·색 공간·alpha](docs/01-visual-model/04-images-color-and-alpha.md) | 픽셀 값이 무엇을 의미하며 연산은 어느 색 공간에서 해야 합니까? |
| 05 | [샘플링·필터링·aliasing](docs/01-visual-model/05-sampling-filtering-and-aliasing.md) | 연속 신호를 유한 픽셀과 texel로 옮길 때 어떤 정보가 사라집니까? |

### Part 2. CPU 소프트웨어 래스터화

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 06 | [삼각형 setup·coverage·fill rule](docs/02-software-rasterization/06-triangle-setup-coverage-and-fill-rules.md) | 한 픽셀 sample이 정확히 어느 삼각형에 속합니까? |
| 07 | [보간·원근 보정·미분값](docs/02-software-rasterization/07-interpolation-perspective-and-derivatives.md) | vertex 값은 fragment까지 어떻게 전달되며 왜 `1/w`가 필요합니까? |
| 08 | [깊이·culling·blending·투명도](docs/02-software-rasterization/08-depth-culling-blending-and-transparency.md) | 여러 fragment가 같은 sample을 차지할 때 누가 최종값을 소유합니까? |
| 09 | [소프트웨어 래스터라이저 capstone](docs/02-software-rasterization/09-software-rasterizer-capstone.md) | 픽셀 결과뿐 아니라 중간 상태와 오답을 어떻게 검증합니까? |

### Part 3. 조명·asset·장면 구조

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 10 | [normal·조명·material](docs/03-lighting-assets-scene/10-normals-lighting-and-materials.md) | 표면 방향과 빛·재질의 계약을 어떤 공간에서 계산합니까? |
| 11 | [texture·mipmap·normal mapping](docs/03-lighting-assets-scene/11-textures-mipmaps-and-normal-mapping.md) | 확대·축소와 미세 표면 방향을 안정적으로 표현하려면 무엇이 필요합니까? |
| 12 | [mesh·scene·asset 계약](docs/03-lighting-assets-scene/12-meshes-scenes-and-asset-contracts.md) | 외부 asset의 좌표·index·format·참조 오류를 어디서 거부합니까? |
| 13 | [visibility·공간 구조·LOD](docs/03-lighting-assets-scene/13-visibility-spatial-organization-and-lod.md) | 보이지 않는 작업을 줄이면서 결과 계약을 어떻게 보존합니까? |

### Part 4. GPU 실행과 렌더러

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 14 | [GPU 실행과 command 모델](docs/04-gpu-rendering/14-gpu-execution-and-command-model.md) | CPU가 기록한 명령은 언제 GPU에서 실행되고 완료됩니까? |
| 15 | [resource·layout·transfer·format](docs/04-gpu-rendering/15-resources-layouts-transfers-and-formats.md) | buffer와 texture의 내용·용도·수명을 누가 소유합니까? |
| 16 | [shader·pipeline·render pass](docs/04-gpu-rendering/16-shaders-pipelines-and-render-passes.md) | shader interface와 고정 상태는 어떤 pipeline 계약을 이룹니까? |
| 17 | [frame lifecycle·동기화·resize](docs/04-gpu-rendering/17-frame-lifecycle-synchronization-and-resize.md) | 여러 프레임이 동시에 진행될 때 resource 재사용을 어떻게 안전하게 합니까? |
| 18 | [debugging·validation·frame capture](docs/04-gpu-rendering/18-debugging-validation-and-frame-capture.md) | 검은 화면을 추측하지 않고 첫 잘못된 상태를 어떻게 찾습니까? |
| 19 | [성능·profiling·frame budget](docs/04-gpu-rendering/19-performance-profiling-and-frame-budget.md) | CPU·GPU·대역폭·동기화 병목을 어떻게 분리합니까? |
| 20 | [GPU renderer capstone](docs/04-gpu-rendering/20-gpu-renderer-capstone.md) | 소프트웨어 정본과 GPU 결과를 비교하며 렌더러를 어떻게 완성합니까? |

## 실습 경로

[실습 안내](exercises/README.md)는 하나의 누적 C++20 project를 starter·reference·learner workspace 세 구현으로 제공합니다. 각 단계는 **계약, 입력 fixture, 필수 산출물, 알려진 오답, 자동 증거와 사람 검토 질문**을 공유합니다.

```text
01 transform trace
→ 02 sampling과 color
→ 03 triangle coverage
→ 04 perspective·depth·blend
→ 05 textured lit scene
→ 06 GPU first frame
→ 07 frame debugging
→ 08 renderer capstone
```

각 실습의 `contract.json`은 검사기가 읽는 최소 정본입니다. `exercises/08-renderer-capstone/project/starter/`의 `TODO`를 단계별로 구현하고, 같은 project의 결정적 `reference`와 공개 checker를 사용해 다음을 확인합니다.

- 어떤 입력을 읽는가
- 어떤 artifact를 생성하는가
- 어떤 불변식을 지켜야 하는가
- 어떤 잘못된 구현이 반드시 거부돼야 하는가
- 무엇을 제출해야 완료로 판단하는가

`scripts/new-workspace.sh`는 starter를 Git에서 제외된 `workspace/`로 한 번만 원자 복사하며 기존 학습자 작업을 덮어쓰지 않습니다. `exercises/check.py`는 `starter`가 `not-implemented`, 올바른 `reference`가 `pass`, 완성한 `workspace`가 단계별 `pass`인지 확인합니다. 이미지 비교에는 표준 라이브러리만 사용하는 [`tools/ppm_diff.py`](tools/ppm_diff.py)를 사용합니다. 이는 작은 결정적 fixture를 위한 도구이며, 사람의 지각 품질이나 모든 GPU 차이를 대신 판정하지 않습니다.

## 구현 프로필

### 필수 프로필: CPU 정본

- C++20과 CMake
- 외부 수학·이미지 라이브러리 없이 핵심 변환과 rasterization 구현
- PPM 이미지와 JSON trace를 artifact로 사용
- 고정 입력·고정 sample 위치·명시적 rounding 규칙

### 권장 프로필: SDL3 GPU

GPU 개념은 Vulkan·Metal·Direct3D 12 계열의 명시적 모델을 기준으로 설명하고, 첫 이식 구현은 SDL3 GPU API를 권장합니다. SDL3는 window·device·command buffer·render pass·pipeline·resource의 경계를 비교적 작게 드러내면서 여러 backend를 사용할 수 있습니다.

SDL3 자체와 shader compiler binary는 이 브랜치에 vendoring하지 않습니다. 설치·버전·backend·shader format은 [SDL3 GPU 구현 프로필](docs/90-appendix/02-api-profile-sdl3-gpu.md)과 [버전 기준](reference/version-baseline.md)에서 확인합니다.

### 번들 reference와 최종 학습자 증거의 경계

CPU reference는 고정 fixture에서 비자명한 left-handed camera, 여섯 homogeneous clip plane을 가로지르는 attribute 보존 clipping, 화면에서 affine한 NDC depth, `SceneSnapshot`의 vertex color·normal과 marker texture·단순 lighting을 실제로 계산합니다. 공개 checker는 독립 계산과 golden artifact로 mutation의 첫 차이, culling/LOD의 선택과 work count까지 확인합니다. 반면 cube 전체, mirrored-UV TBN과 범용 외부 asset loader는 번들 자동 구현이 아니라 learner 구현과 사람 검토 범위입니다.

현재 번들 SDL reference가 실제 GPU에서 자동 확인하는 범위는 **동일한 고정 scene id와 position·vertex color를 쓰는 indexed triangle**, RGBA8 color·D16 depth offscreen pass와 같은 Metal device 안의 좁은 lifecycle probe입니다. probe는 실제 frame slot 2개로 submission 3개를 수행하고, completion 뒤 slot 0을 재사용하며, zero extent에서 target을 만들지 않고, 64×64 generation에서 96×72 generation으로 바꾼 뒤 이전 resource를 retire하고 새 color/depth를 readback합니다. 현재 MSL/HLSL shader는 position과 vertex color만 소비하므로 actual GPU 비교가 통과해도 문서 10–11과 실습 05의 texture·normal·lighting 전체가 GPU로 이전됐다는 증거는 아닙니다.

학습자는 [GPU renderer capstone](docs/04-gpu-rendering/20-gpu-renderer-capstone.md)의 전체 범위에 따라 texture/material/lighting debug attachment, 실제 window/swapchain resize·minimize·high-DPI 또는 그 미지원 근거, capture label 대응과 진짜 GPU timestamp를 별도로 제출합니다. 실제 offscreen extent 전이와 lifecycle simulator는 window event의 대체 증거가 아니며, `submit_to_fence_ns`도 CPU wall time이지 GPU pass duration이 아닙니다.

## 준비와 검증

새 checkout에서 실행합니다.

```sh
./prepare.sh
./scripts/new-workspace.sh

cmake -S exercises/08-renderer-capstone/project \
  -B build/workspace \
  -DCG_IMPLEMENTATION=workspace \
  -DCG_GPU=auto
cmake --build build/workspace
ctest --test-dir build/workspace --output-on-failure

python3 exercises/check.py \
  --impl workspace \
  --stage 01-transform-trace \
  --expect not-implemented \
  --gpu auto

./verify.sh
```

마지막 명령의 `not-implemented`는 새 workspace의 공개 미완성 상태가 정확히 검출됐다는 뜻입니다. 해당 단계를 구현한 뒤 `--expect pass`로 바꿉니다. 결정적 기준선은 같은 방식으로 `--impl reference --stage all --expect pass --gpu off`를 실행하고, starter의 음성 대조군은 `--impl starter --stage all --expect not-implemented --gpu off`로 확인합니다. 실제 GPU 완료 증거가 필요할 때만 지원 환경에서 `--gpu required`를 사용합니다. `auto`에서 장비가 없어 생략된 필수 GPU 검사는 성공으로 바뀌지 않으며 보고서에 제한으로 남습니다.

`prepare.sh`는 다음만 수행합니다.

- Python과 저장소 구조 확인
- C++ compiler·CMake·SDL3·RenderDoc 같은 선택 도구의 존재 여부 기록
- 문서와 계약 입력의 SHA-256 지문 생성
- `.guide/computer-graphics/prepared.json` 작성

운영체제 package를 자동 설치하거나 source를 수정하지 않습니다.

`verify.sh`는 원본 밖 임시 복사본에서 다음을 검사합니다.

- 정본 디렉터리, 문서·상대 링크·anchor와 실습 `contract.json`
- repository verifier의 의도적 문서·계약 변조 거부
- PPM oracle, starter의 명시적 미완성 경계와 reference 공개 행동
- known-bad mutation 거부와 learner workspace 비파괴 생성
- release build·CTest와 지원 compiler의 sanitizer
- `VERIFY_GPU=auto|required|off`에 따른 실제 GPU 평가 또는 명시적 미평가
- 임시 검증 뒤 원본 source 지문과 tracked Git 상태 불변

`verify.sh`는 저장소와 공개 구현의 회귀 근거를 검사합니다. 검사 통과만으로 설명의 교육적 충분성, texture/lighting GPU parity, 실제 window resize·high-DPI, 외부 capture file, 장시간 device-loss 동작이나 실행하지 않은 backend가 증명되지는 않습니다. 각 실습의 사람 검토 루브릭과 [안전 및 운영 계약](SAFETY.md)을 함께 적용합니다.

빠른 구조 검사는 다음으로 실행할 수 있습니다.

```sh
make check
```

생성물을 정리할 때는 `make clean`으로 `.guide/`, `build/`, `out/`만 제거합니다. 학습자 `workspace/`는 자동 삭제하지 않습니다. workspace가 손상됐다면 먼저 다른 위치에 보존한 뒤 직접 이름을 바꾸고 `./scripts/new-workspace.sh`로 새 사본을 만듭니다.

## 완료 뒤 할 수 있어야 하는 일

- local vertex가 최종 pixel이 되는 각 공간과 상태 전이를 추적합니다.
- clipping, fill rule, perspective-correct interpolation과 depth/blend 결과를 결정적 fixture로 검증합니다.
- color space, alpha 표현, texture filtering과 mip 선택 오류를 구분합니다.
- mesh와 scene asset의 좌표·format·index·수명 계약을 검사합니다.
- GPU resource, shader interface, pipeline, command buffer, render pass와 frame lifetime을 설명합니다.
- validation message와 frame capture에서 첫 잘못된 resource·state·draw를 찾습니다.
- CPU·GPU frame time, queue wait, draw 수, 대역폭과 overdraw 근거를 분리해 성능 변경을 검토합니다.
- 기존 renderer 또는 graphics tool 저장소에서 작은 bug·feature·test 변경을 시작합니다.

## 의도적으로 다루지 않는 범위

- C++ 언어·CMake·RAII의 재교육
- 일반 선형대수·수치해석 전체
- 게임 엔진 편집기·물리·게임플레이·오디오
- ray tracing API, path tracing과 전역 조명 전문 과정
- animation·skinning·particle·terrain의 완성 구현
- GPU compute kernel·driver·compiler 개발
- 특정 API의 모든 extension과 플랫폼별 배포
- 상용 asset 제작 도구의 사용법

이 가이드의 종료점은 완성된 게임 엔진이나 최첨단 renderer가 아닙니다. **그래픽스 결과를 상태·수학·resource·동기화·측정 근거로 설명하고, 실제 그래픽스 프로젝트에 진입할 수 있는 상태**입니다.

기여·출처·배포 조건은 [기여 가이드](CONTRIBUTING.md), [안전 및 운영 계약](SAFETY.md), [라이선스](LICENSE.md)에서 확인합니다.
