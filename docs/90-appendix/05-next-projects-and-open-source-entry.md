# 다음 프로젝트와 오픈소스 진입

## 목적

이 가이드를 끝낸 뒤 tutorial renderer를 반복하는 대신 실제 graphics codebase의 문서·test·loader·tool·renderer 하위 시스템에 기여하는 경로를 제시합니다. 프로젝트 이름보다 첫 변경의 범위와 증거를 기준으로 선택합니다.

## 준비 상태 확인

다음이 가능하면 외부 프로젝트로 이동합니다.

- build와 sample을 재현합니다.
- 한 draw의 resource·pipeline·attachment를 capture에서 찾습니다.
- coordinate/color/format convention을 문서와 코드에서 복원합니다.
- 작은 image fixture와 numeric trace를 추가할 수 있습니다.
- CPU/GPU lifetime과 thread ownership을 구분합니다.
- performance claim에 before/after 환경과 timing을 붙입니다.

## 첫 기여 유형

### 문서와 sample 검증

- 오래된 API 이름·build 명령 수정
- sample의 coordinate/color convention 명시
- screenshot만 있는 예제에 validation·error handling 추가
- supported backend와 shader build 과정 보완

문서 변경도 실제 명령과 sample을 실행해 검증합니다.

### asset validation

- out-of-range index 또는 invalid accessor 거부
- row stride·format·sRGB metadata 오류 수정
- cyclic scene hierarchy 검출
- malformed asset fixture와 error message 추가

asset loader는 입력이 명확하고 regression fixture를 만들기 쉬워 첫 코드 기여로 적합합니다.

### rendering regression

- 특정 culling/depth/blend state의 작은 scene
- resize·zero extent·high-DPI regression
- shader binding/layout mismatch 검사
- resource reload와 deferred destruction 테스트
- software image 또는 readback 기반 comparison

최종 screenshot보다 첫 잘못된 attachment를 드러내는 fixture를 선호합니다.

### tooling

- shader manifest/reflection generator
- image diff report
- frame artifact 정리 도구
- pipeline/resource label 개선
- capture 재현 명령과 bug report template

다른 개발자가 문제를 좁히는 시간을 줄이는 도구는 높은 레버리지를 갖습니다.

### 성능

첫 기여로 거대한 renderer rewrite를 제안하지 않습니다.

1. reproducible workload를 추가합니다.
2. CPU/GPU 어느 구간인지 확인합니다.
3. 작은 변경을 적용합니다.
4. correctness artifact와 frame-time distribution을 함께 제출합니다.
5. memory·complexity·platform 비용을 기록합니다.

## 프로젝트 선택 분야

### renderer·engine

scene, resource, shader, pass와 frame lifecycle을 직접 다룹니다. 처음에는 loader bug, regression scene, debug label 또는 특정 backend issue처럼 경계가 작은 문제를 선택합니다.

### graphics API wrapper와 window library

backend abstraction, shader format, swapchain과 platform lifecycle을 다룹니다. 최소 재현과 여러 backend의 실제 계약을 확인해야 합니다.

### asset·image·mesh library

format validation, decoding, color/alpha metadata, tangent와 scene hierarchy를 다룹니다. security boundary가 될 수도 있으므로 malformed input과 size overflow를 함께 검사합니다.

### visualization·CAD·creative tool

정확한 coordinate, picking, large scene, image/color output와 UI integration이 중요합니다. renderer만이 아니라 사용자 작업 상태와 export artifact를 이해해야 합니다.

### browser/WebGPU

WebGPU API와 WGSL, validation, conformance와 backend translation을 다룹니다. W3C specification과 implementation test를 정본으로 사용하며, 브라우저 build 규모에 맞춰 test/diagnostic부터 시작할 수 있습니다.

### offline renderer

camera·asset·material·sampling과 image oracle을 재사용하지만 Monte Carlo, acceleration structure와 path transport를 추가로 학습합니다. rasterizer 성능 기술을 그대로 적용하지 않습니다.

## issue 조사 절차

```text
issue와 기여 지침 읽기
→ 현재 main에서 재현
→ 최소 scene/input 만들기
→ 마지막 정상/첫 비정상 단계 찾기
→ project convention과 test style 확인
→ 작은 patch
→ validation·image·performance 근거
→ 범위와 미해결 항목 기록
```

maintainer에게 설계 방향이 필요한 문제는 큰 구현 전에 재현과 조사 결과를 공유합니다.

## 포트폴리오에 남길 것

- fixed scene/input과 실행 명령
- coordinate/resource/frame lifecycle 그림 또는 표
- frame capture event와 debug label
- before/after attachment diff
- known-bad mutation 또는 regression test
- CPU/GPU timing raw sample과 환경
- review에서 바뀐 설계와 이유

화려한 screenshot만으로는 문제 해결 능력을 보여 주기 어렵습니다.

## 피해야 할 경로

- engine을 처음부터 전부 만드는 일만 반복
- API sample을 복사하고 state 의미를 설명하지 않음
- shader effect 수를 늘리는 것을 깊이로 착각
- reference image를 업데이트해 regression 제거
- 다른 GPU 결과를 확인하지 않고 driver bug로 단정
- 성능 수치 없이 “batching”, “multithread”, “GPU-driven”을 적용

## 다음 전문화

가이드 이후 관심에 따라 다음을 별도 프로젝트로 확장합니다.

- physically based rendering과 image-based lighting
- shadow·deferred/forward+·post-processing
- animation·skinning과 character rendering
- GPU-driven rendering, meshlet과 frame graph
- ray tracing과 path tracing
- rendering architecture·resource allocator·pipeline cache
- color management·HDR·display pipeline
- WebGPU/Vulkan/Metal/D3D12 전문 구현
- graphics compiler·shader toolchain

한 번에 모두 진행하지 않고 실제 프로젝트의 하위 시스템 하나에서 반복 기여합니다.
