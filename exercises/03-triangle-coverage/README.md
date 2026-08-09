# 실습 03 — triangle coverage

## 목적

edge function, pixel center와 top-left fill rule로 삼각형 coverage를 결정합니다. 두 triangle이 rectangle을 이룰 때 모든 내부 sample이 정확히 한 primitive에 속하고, winding·clipping·scissor·degenerate 입력을 결정적으로 처리합니다.

관련 문서:

- [삼각형 setup·coverage](../../docs/02-software-rasterization/06-triangle-setup-coverage-and-fill-rules.md)
- [카메라·projection·clipping](../../docs/01-visual-model/03-camera-projection-and-clipping.md)

## 입력 fixture

작은 8×8 또는 16×16 framebuffer를 사용합니다.

- axis-aligned right triangle
- 두 triangle로 나눈 rectangle
- shared horizontal/vertical/diagonal edge
- clockwise와 counter-clockwise 입력
- framebuffer 밖에 걸친 triangle
- clip plane 뒤 생성된 triangle
- collinear/duplicate vertex
- scissor 사각형

## 구현할 경계

```text
screen vertex
→ signed area/winding
→ culling/degenerate
→ sample-aware integer bounding box
→ edge equation와 top-left flag
→ sample coverage
→ primitive-id attachment
```

가능하면 subpixel fixed-point 또는 명시적인 quantization을 사용합니다. float 구현이라면 equality와 rounding 정책을 fixture에 고정합니다.

## 필수 artifact

```text
out/coverage/
├── case-*.ppm
├── case-*-primitive-id.json
├── setup-trace.json
├── coverage-counts.json
└── mutation-report.json
```

primitive-id artifact는 sample별 0(배경), triangle id 또는 overlap sentinel을 기록합니다.

## 불변식

- rectangle 내부 sample에 gap과 overlap이 없습니다.
- vertex 순서를 front-face로 정규화하면 결과 집합이 같습니다.
- degenerate triangle은 0 sample을 생성하고 0으로 나누지 않습니다.
- bounding box 밖 sample을 검사하거나 쓰지 않습니다.
- scissor 밖 write가 없습니다.
- clipping child triangle의 union이 clipped polygon을 덮습니다.

## 알려진 오답

- 모든 edge `>=0`
- 모든 edge `>0`
- integer cast 기반 잘못된 negative bounding box
- viewport Y가 바뀌었지만 front face 유지
- degenerate area로 barycentric 계산

## 완료 근거

- fixture별 image와 sample count
- shared-edge gap/overlap 자동 assertion
- setup trace의 area, edge coefficient, top-left flag와 bounds
- 알려진 오답 최소 세 개가 정확한 case에서 실패
- quantization과 경계 equality 결정 기록

## 준비·workspace·stage 검사

[공통 workspace 절차](../README.md#workspace-준비와-공개-명령)로 만든 learner 사본을 사용합니다. 기존 workspace는 다시 생성하지 않습니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/workspace -DCG_IMPLEMENTATION=workspace -DCG_GPU=off
cmake --build build/workspace
python3 exercises/check.py --impl workspace --stage 03-triangle-coverage --expect pass --gpu off
python3 exercises/check.py --impl reference --stage 03-triangle-coverage --expect pass --gpu off
```

checker는 shared edge의 gap/overlap, winding 정규화, degenerate 0-write, framebuffer·scissor 경계와 primitive-id 결과를 reference와 비교합니다. starter와 최소 세 known-bad mutation이 올바른 fixture에서 거부돼야 합니다.

사람 검토에서는 top-left equality와 subpixel quantization을 왜 그 방식으로 고정했는지, clipping child triangle의 union을 어떻게 확인했는지, 음수 좌표 bounding box에서 단순 cast가 왜 틀리는지 설명합니다.

`make clean`은 생성물만 제거합니다. 실패한 primitive-id map과 setup trace는 보존하고 첫 다른 edge 판정부터 복구합니다. workspace 자체는 자동 삭제·덮어쓰기하지 않습니다.
