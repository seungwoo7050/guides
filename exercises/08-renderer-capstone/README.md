# 실습 08 — renderer capstone

## 목적

CPU software renderer와 GPU renderer가 같은 scene·좌표·색·alpha·sample 계약을 소비하게 하고, transform부터 final image까지 단계별 artifact를 비교합니다. 완성 화면뿐 아니라 resource/frame lifecycle, validation, capture와 performance budget을 포함해 실제 graphics 프로젝트 진입 기준을 만듭니다.

관련 문서:

- [software rasterizer capstone](../../docs/02-software-rasterization/09-software-rasterizer-capstone.md)
- [GPU renderer capstone](../../docs/04-gpu-rendering/20-gpu-renderer-capstone.md)
- [다음 프로젝트와 오픈소스](../../docs/90-appendix/05-next-projects-and-open-source-entry.md)

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
