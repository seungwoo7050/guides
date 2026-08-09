# 실습 01 — transform trace

## 목적

고정 scene의 vertex·direction·normal을 local에서 viewport까지 추적해 행렬 순서, handedness, camera, clipping과 viewport convention을 수치로 검증합니다. 최종 점 하나만 출력하지 않고 첫 잘못된 공간을 찾을 수 있는 trace를 만듭니다.

관련 문서:

- [좌표 공간과 변환](../../docs/01-visual-model/02-coordinate-spaces-and-transforms.md)
- [카메라·투영·클리핑](../../docs/01-visual-model/03-camera-projection-and-clipping.md)
- [수학 규약](../../docs/90-appendix/01-math-conventions-and-formulas.md)

## 초기 상태

다음 case를 코드 또는 JSON fixture로 고정합니다.

1. identity triangle
2. translation·rotation·non-uniform scale object
3. parent-child transform
4. near plane을 가로지르는 triangle
5. invalid camera up/forward
6. zero scale로 singular normal matrix가 되는 object

각 fixture에 stable id와 expected validity를 둡니다.

## 구현할 경계

```text
scene fixture
→ model/world transform
→ camera view
→ projection
→ homogeneous clip code와 intersection
→ perspective divide
→ viewport
→ trace JSON
```

행렬 storage order와 수학 convention을 trace header에 기록합니다. normal은 position과 다른 경로를 사용합니다.

## 필수 artifact

```text
out/transform-trace/
├── conventions.json
├── case-identity.json
├── case-nonuniform.json
├── case-hierarchy.json
├── case-near-clip.json
└── rejected.json
```

vertex trace 항목:

- local/world/view/clip/NDC/viewport 값
- clip `w`와 plane별 inside/outside
- 생성된 intersection vertex와 원본 edge
- matrix hash
- finite/range 검사

normal trace에는 model normal matrix, 변환 전후 길이와 tangent dot를 포함합니다.

## 검사할 불변식

- identity 결과가 입력과 같습니다.
- direction에는 translation이 적용되지 않습니다.
- normal과 transformed tangent가 수치 오차 안에서 수직입니다.
- hierarchy 합성이 `parent_world * child_local`입니다.
- clipping 뒤 vertex가 모든 clip plane을 만족합니다.
- 유효 결과의 NDC와 viewport 값은 finite입니다.
- viewport center와 corner mapping이 과정 규약과 같습니다.

## 알려진 오답

- `M * V * P`로 순서 교환
- `w`를 perspective divide 전에 버림
- normal에 model matrix 직접 적용
- viewport Y flip 중복
- outside vertex가 하나면 triangle 전체 제거

각 오답은 어느 JSON field에서 처음 달라지는지 기록합니다.

## 완료 근거

- 모든 필수 artifact
- case별 자동 assertion 결과
- 오답 mutation 최소 두 개의 실패 로그
- convention을 다른 API profile로 옮길 때 필요한 변환표
- 구현하지 않은 수치 안정성 범위
