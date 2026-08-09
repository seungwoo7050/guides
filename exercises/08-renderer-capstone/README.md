# 실습 08 — renderer capstone

## 목적

CPU software renderer와 GPU renderer가 같은 scene·좌표·색·alpha·sample 계약을 소비하게 하고, transform부터 final image까지 단계별 artifact를 비교합니다. 완성 화면뿐 아니라 resource/frame lifecycle, validation, capture와 performance budget을 포함해 실제 graphics 프로젝트 진입 기준을 만듭니다.

관련 문서:

- [software rasterizer capstone](../../docs/02-software-rasterization/09-software-rasterizer-capstone.md)
- [GPU renderer capstone](../../docs/04-gpu-rendering/20-gpu-renderer-capstone.md)
- [다음 프로젝트와 오픈소스](../../docs/90-appendix/05-next-projects-and-open-source-entry.md)

## 번들 reference와 learner 완료 범위

| 구분 | 자동 reference 근거 | learner가 추가해 사람이 확인할 근거 |
|---|---|---|
| software | nontrivial LH camera, six-plane attribute clip, screen-affine NDC depth, `SceneSnapshot` vertex color·normal+texture+단순 lighting, mutation 첫 차이와 culling/LOD work artifact | cube·mirrored TBN·범용 loader, 설계 설명, 새 fixture와 tolerance 선택의 근거 |
| actual GPU | 동일 scene id의 position·vertex-color indexed triangle과 RGBA8+D16 readback; 같은 Metal device의 2 slots·3 submits·12 events와 64×64→96×72 offscreen generation·readback·retire | texture/sampler/material/normal/lighting GPU 경로, window/swapchain resize·minimize·high-DPI와 단계별 debug attachment |
| lifecycle/debug | completion·generation·zero extent 상태 모델의 실제 transition과 mutation 거부, 명시적으로 synthetic인 before/workload report | 실제 driver validation·capture file, GPU timestamp와 대표 raw workload |

현재 MSL/HLSL shader는 position과 vertex color만 사용합니다. actual GPU readback이 CPU의 고정 color triangle과 일치해도 아래 필수 scene의 texture·normal·lighting 전체가 GPU로 이전됐다고 판정하지 않습니다. 이 표는 요구사항을 줄이는 면제가 아니라 자동 reference가 제공하는 출발 근거와 학습자의 종료 증거를 구분합니다.

## 필수 scene

- RGB/clip/shared-edge 기본 fixture
- perspective checker quad
- indexed textured mesh
- non-uniform scale과 normal lighting
- 앞/뒤 opaque object
- alpha mask 또는 transparent layer
- frustum 밖 object와 LOD 두 단계
- resize·asset generation 변경 case

## 필수 subsystem

### software

- transform·clipping·top-left coverage
- perspective attribute·depth
- texture/color/alpha
- PPM/depth/id/trace artifact

### GPU

- device·shader manifest·resource upload
- pipeline와 color/depth pass
- frame slots·completion·resize
- debug label·validation·readback/capture
- CPU/GPU timing

### shared

- scene snapshot과 asset validation
- convention/version manifest
- stable object/primitive/material id
- comparison report

## 제출 구조 예시

```text
capstone/
├── README.md
├── conventions.json
├── scenes/
├── software/
├── gpu/
├── tests/
├── artifacts/
│   ├── software/<case>/
│   ├── gpu/<case>/
│   └── comparisons/<case>/
└── reports/
    ├── correctness.md
    ├── debugging.md
    └── performance.md
```

## 비교 순서

1. scene/camera/settings와 shader/material manifest
2. input/clipped/culled primitive count
3. primitive id·coverage
4. depth
5. UV·normal·material debug
6. linear color
7. final sRGB output

앞 단계가 다르면 뒤 단계의 tolerance를 넓혀 통과시키지 않습니다.

## 알려진 오답 suite

최소 다음 여덟 개 중 여섯 개를 자동 또는 반복 가능한 방법으로 거부합니다.

- matrix order
- clipping 생략
- top-left equality
- affine UV
- sRGB decode 생략
- depth convention 반전
- alpha blend mismatch
- vertex layout/binding mismatch
- frame slot overwrite
- resize stale attachment

## 성능 보고서

세 workload를 사용합니다.

- draw가 많은 작은 object
- fragment가 많은 fullscreen/고해상도
- triangle·material이 많은 scene

환경, raw sample, median/p95, CPU/GPU pass, correctness hash와 한 가지 변경의 전후를 기록합니다. 개선이 없다면 병목이 아니었다는 근거를 제출합니다.

## 완료 판정

- `contract.json`의 artifact와 불변식을 만족합니다.
- software와 GPU 차이의 첫 단계를 case별로 설명합니다.
- validation fatal이 없고 warning baseline이 설명됩니다.
- resize, reload와 종료 수명이 trace에서 안전합니다.
- known-bad suite가 실제로 실패합니다.
- 실제 오픈소스 또는 후속 프로젝트에서 선택할 첫 하위 시스템과 issue 조사 계획을 작성합니다.

## 준비·workspace·누적 검사

[공통 workspace 절차](../README.md#workspace-준비와-공개-명령)로 만든 한 project에서 01–07의 구현과 artifact를 그대로 누적합니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/workspace -DCG_IMPLEMENTATION=workspace -DCG_GPU=auto
cmake --build build/workspace
ctest --test-dir build/workspace --output-on-failure
python3 exercises/check.py --impl workspace --stage 08-renderer-capstone --expect pass --gpu auto
python3 exercises/check.py --impl workspace --stage all --expect pass --gpu auto
python3 exercises/check.py --impl reference --stage all --expect pass --gpu off
```

reference의 `gpu off` 실행은 06과 08을 `GPU_NOT_EVALUATED`로 남기고 01–05 CPU와 07 lifecycle 기준선을 검사합니다. “같은 장면을 GPU pipeline으로 옮긴다”는 종료 능력의 최소 actual 근거는 지원 환경의 `--gpu required` color/depth readback입니다. 전체 capstone 완료에는 texture/material/lighting GPU artifact, 실제 window/swapchain resize·minimize·high-DPI, capture와 GPU timestamp 또는 각 미지원 한계를 별도 제출해야 합니다.

자동 증거는 scene/hash·primitive·extent와 고정 color/depth 비교, resource/pipeline/validation artifact, model과 actual completion/generation trace, declared known-bad 거부와 세 workload report의 schema·통계를 검사합니다. `--gpu required`의 workload는 실제 Metal offscreen submit/fence를 반복하지만 `submit_to_fence_ns`는 CPU wall time이고 GPU timestamp가 아닙니다. 현재 자동 비교에는 GPU texture/normal/material input이나 linear lighting attachment가 없으며 offscreen extent 전이는 actual window/swapchain resize나 capture 근거가 아닙니다. starter의 `not-implemented`도 성공으로 오인되지 않아야 합니다.

사람 검토에서는 다음을 최종 확인합니다.

- software/GPU 차이가 처음 발생한 단계와 허용 tolerance 근거는 무엇입니까?
- resource last-use와 frame slot completion을 어떤 trace로 입증합니까?
- 성능 변경이 correctness hash, memory와 이식성 비용을 어떻게 보존했습니까?
- 카탈로그의 세 종료 능력 각각을 어느 artifact가 증명합니까?
- actual GPU shader가 texture·normal·light를 소비한다는 것을 어떤 binding manifest와 debug attachment가 증명합니까?
- resize/capture/timestamp가 simulation인지 실제 device evidence인지 어디에 표시했습니까?

`make clean`은 `.guide/`, `build/`, `out/`만 제거하고 learner workspace는 보존합니다. 복구 시 기존 workspace와 실패 report를 먼저 별도 보존한 뒤 새 starter 사본을 만들며 reference/expected를 학습자 결과로 덮어쓰지 않습니다.
