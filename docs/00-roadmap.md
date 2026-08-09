# 컴퓨터 그래픽스 학습 로드맵과 범위 계약

## 이 가이드가 해결하는 문제

그래픽스 입문은 흔히 API 초기화, 삼각형 출력, shader 복사로 시작합니다. 화면이 나오면 빠르게 성취감을 얻지만 다음 문제가 생겼을 때 원인을 분리하기 어렵습니다.

- 삼각형 일부가 사라지거나 경계에 틈이 생깁니다.
- 가까운 물체가 먼 물체 뒤로 들어갑니다.
- texture가 뒤집히거나 축소 시 번쩍입니다.
- 조명은 맞아 보이지만 camera를 움직이면 normal이 깨집니다.
- sRGB texture와 linear 값이 섞여 결과가 지나치게 어둡거나 밝습니다.
- resize나 여러 프레임 처리 뒤 GPU resource가 잘못 재사용됩니다.
- GPU가 느린지 CPU가 느린지 모른 채 draw call 수나 shader를 임의로 바꿉니다.

이 과정은 화면 결과를 만드는 “요령”보다 다음 연결을 먼저 고정합니다.

```text
장면 값과 규약
→ 좌표 변환과 clip volume
→ primitive coverage와 fragment 값
→ depth·blend·color 연산
→ image artifact
→ GPU resource·command·동기화
→ frame capture와 profile 근거
```

## 대상 독자

다음을 전제로 합니다.

- C++20으로 여러 파일 프로그램을 만들고 CMake target을 구성할 수 있습니다.
- 값과 참조, 자원 수명, RAII와 오류 처리를 설명할 수 있습니다.
- 배열·벡터·행렬과 기본 자료구조를 코드로 표현할 수 있습니다.
- 컴파일 오류, 실행 오류, 잘못된 결과와 성능 문제를 구분합니다.
- 작은 테스트와 명령을 이용해 변경 전후 결과를 비교할 수 있습니다.

이 기준이 부족하면 [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)의 필요한 문서로 이동합니다. 세 브랜치를 전부 다시 완료할 필요는 없습니다.

## 이 가이드가 고정하는 규약

그래픽스 오류의 상당수는 서로 다른 관례를 암묵적으로 섞을 때 발생합니다. 과정 전체에서 다음을 정본으로 사용합니다.

| 항목 | 과정 규약 |
|---|---|
| 벡터 표기 | column vector |
| 변환 합성 | `clip = P * V * M * local`이며 오른쪽 변환부터 적용 |
| world/view handedness | left-handed, camera forward는 `+Z` |
| clip/NDC 깊이 | z는 `[0, 1]`, near가 `0`, far가 `1` |
| NDC x·y | `[-1, 1]` |
| viewport 원점 | 왼쪽 위, `+Y`는 아래 |
| texture 좌표 원점 | 왼쪽 위, `+V`는 아래 |
| pixel sample | 기본은 pixel center `(x + 0.5, y + 0.5)` |
| 앞면 | viewport 변환 뒤 counter-clockwise |
| 색 연산 | 조명·필터링·blending은 linear RGB |
| 출력 | 표시용 color target에서 sRGB encoding |
| alpha | 입력 의미를 명시하며 기본 설명은 straight alpha, 경계 혼합은 premultiplied 권장 |

특정 API·asset·image가 다른 규약을 사용하면 입구에서 한 번 변환하고 내부 정본을 유지합니다. shader마다 임시로 축을 뒤집거나 camera·texture·asset에 서로 다른 규칙을 숨기지 않습니다.

## 학습 단계와 누적 산출물

### 1단계: 시각 결과의 계약

문서 01–05와 실습 01–02를 진행합니다.

산출물:

- 좌표 공간별 vertex trace
- camera와 projection parameter의 유효성 검사
- clip·NDC·viewport 변환 표
- linear/sRGB와 alpha 변환 fixture
- nearest/bilinear sample의 기준 결과

이 단계의 핵심은 수식 암기가 아닙니다. 값이 어느 공간·단위·범위를 갖는지 타입·이름·artifact에서 확인 가능하게 만드는 것입니다.

### 2단계: 소프트웨어 rasterization

문서 06–09와 실습 03–04를 진행합니다.

산출물:

- edge function과 top-left rule 결과
- degenerate·clipped triangle 처리 기록
- barycentric·`1/w`·depth trace
- depth·culling·blending 전후 attachment
- PPM 최종 이미지와 JSON 통계

작은 해상도와 고정 장면을 사용합니다. 속도가 아니라 픽셀 소유권과 오답 판정이 기준입니다.

### 3단계: 장면의 의미

문서 10–13과 실습 05를 진행합니다.

산출물:

- normal transform과 공간 선택 근거
- linear 조명 결과와 material parameter
- mip chain과 texture footprint 기록
- mesh/index/scene validation 보고서
- frustum culling과 LOD 선택 통계

물리 기반 렌더링 전체를 구현하지 않습니다. 조명 방정식의 입력·단위·범위와 asset 계약을 검증하는 기준선을 만듭니다.

### 4단계: GPU 이전

문서 14–20과 실습 06–08을 진행합니다.

산출물:

- device와 backend 정보
- resource 생성·upload·사용·retire trace
- shader reflection 또는 명시적 binding 계약
- frame timeline과 frames-in-flight 상태
- validation message·debug marker·frame capture
- CPU/GPU timing과 frame budget 표
- software/GPU image 비교 보고서

GPU 결과가 다르면 “부동소수점 차이”라고 바로 결론 내리지 않습니다. 좌표·coverage·보간·format·shader interface·resource 상태 중 첫 차이를 좁힙니다.

## 구현 프로필

### CPU 정본 프로필

다음은 필수입니다.

- C++20
- CMake 3.20 이상 권장
- 표준 라이브러리만으로 핵심 수학과 rasterizer 구현
- PPM(P6 또는 P3) artifact
- JSON 또는 line-oriented trace
- 고정 seed와 결정적 fixture

고성능 수학 라이브러리, image loader와 scene loader는 나중에 교체할 수 있습니다. 첫 구현에서 외부 라이브러리가 좌표·rounding·filtering 규칙을 숨기지 않게 합니다.

### GPU 이식 프로필

권장 첫 경로는 SDL3 GPU API입니다.

- SDL3 window와 GPU device
- command buffer와 copy/render pass
- vertex/index/uniform buffer
- texture·sampler·depth attachment
- graphics pipeline과 shader
- swapchain acquire·submit·resize

SDL3는 학습 도구일 뿐 소유 개념이 아닙니다. 문서의 resource·pipeline·synchronization 계약은 Vulkan, Metal, Direct3D 12, WebGPU 같은 명시적 API에서 다시 읽을 수 있어야 합니다.

shader source와 binary format은 환경에 맞게 선택하되 다음을 기록합니다.

- 원본 shader 언어와 compiler 버전
- 생성 형식(SPIR-V, DXIL, MSL/metallib 등)
- entry point와 stage
- binding layout과 vertex input
- build 명령과 artifact hash

## 문서와 실습 대응

| 문서 범위 | 실습 | 핵심 오답 |
|---|---|---|
| 01–03 | `01-transform-trace` | 행렬 순서, handedness, `w` 처리, near/far 오류 |
| 04–05 | `02-sampling-and-color` | sRGB 값 직접 평균, texel center, alpha 혼합 오류 |
| 06 | `03-triangle-coverage` | shared edge 틈/중복, winding, degenerate 처리 |
| 07–08 | `04-perspective-depth-blend` | affine UV, depth 범위, blend order·alpha 표현 |
| 10–13 | `05-textured-lit-scene` | normal 공간, mip 선택, invalid index, culling 오답 |
| 14–17 | `06-gpu-first-frame` | shader interface, resource lifetime, acquire/submit 순서 |
| 18–19 | `07-frame-debugging` | validation 무시, GPU/CPU timing 혼동, 근거 없는 최적화 |
| 전체 | `08-renderer-capstone` | software/GPU 차이를 최종 화면만 보고 추측 |

## 경로 선택

### graphics application 또는 visualization에 진입

01–13을 모두 진행하고 GPU 문서 14–18을 따라 첫 renderer를 만듭니다. 19의 측정 기준을 적용한 뒤 외부 GUI·scientific visualization·CAD 프로젝트로 이동합니다.

### game renderer에 진입

전체 과정을 진행합니다. 이후 animation, shadow, deferred/forward+, post-processing, terrain, particle과 engine integration은 별도 프로젝트에서 확장합니다.

### graphics API·engine infrastructure에 진입

01–09를 생략하지 않습니다. GPU 문서 14–20에서 resource allocator, pipeline cache, upload scheduler, frame graph 같은 하위 시스템으로 이동합니다.

### offline rendering 또는 ray tracing으로 이동

01–05, 10–12가 직접 기반입니다. rasterization의 coverage 규칙은 다른 pipeline이지만 camera·asset·색·sampling·material·검증 계약은 재사용합니다. path tracing과 Monte Carlo estimator는 이 브랜치 밖의 전문 과정입니다.

## 완료 기준

다음을 수행할 수 있으면 가이드의 종료점에 도달합니다.

1. 고정 장면의 vertex 한 개가 local에서 framebuffer sample까지 이동하는 값을 단계별로 기록합니다.
2. clip plane을 가로지르는 삼각형을 올바르게 잘라 유효 primitive로 만듭니다.
3. shared edge에서 틈과 중복이 없는 fill rule을 설명하고 fixture로 검증합니다.
4. perspective-correct interpolation과 affine interpolation이 다른 장면을 만듭니다.
5. linear/sRGB, straight/premultiplied alpha를 입력·연산·저장 경계에서 구분합니다.
6. depth·culling·blend 상태의 순서가 최종 sample에 미치는 영향을 trace로 설명합니다.
7. mesh·texture·scene asset을 렌더링 전에 검증하고 잘못된 참조를 거부합니다.
8. GPU resource와 command가 CPU 수명과 다른 완료 시점을 갖는 이유를 설명합니다.
9. resize와 frames-in-flight 중 사용 중인 resource를 파괴하거나 덮어쓰지 않습니다.
10. frame capture·validation·timestamp·CPU profile에서 첫 잘못된 상태나 병목을 찾습니다.
11. software와 GPU 결과를 허용 오차·mask·중간 attachment와 함께 비교합니다.
12. 실제 graphics 저장소의 작은 rendering bug, loader validation, test 또는 tooling 변경을 시작합니다.

## 의도적으로 다루지 않는 범위

이 과정은 다음을 완성하지 않습니다.

- 상용 game engine 또는 editor
- 복잡한 ECS·scene editor·asset build farm
- animation·skinning·inverse kinematics
- shadow algorithm과 global illumination 전체
- ray tracing pipeline과 denoising
- advanced PBR, spectral rendering과 color management 전문 과정
- GPU compute 최적화, CUDA/HIP와 driver 개발
- VR/AR, multi-view와 display calibration
- 플랫폼별 window/input/audio/product packaging

후속 프로젝트에서 필요한 분야를 고르되, 이 가이드의 규약·artifact·검증 원칙을 유지합니다.
