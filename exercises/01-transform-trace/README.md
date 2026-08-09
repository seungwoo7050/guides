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

## 준비·workspace·stage 검사

저장소 root에서 [공통 workspace 절차](../README.md#workspace-준비와-공개-명령)를 먼저 수행합니다. `workspace/`가 아직 없을 때만 `./scripts/new-workspace.sh`를 실행하며 기존 학습자 파일에는 다시 실행하지 않습니다.

```sh
cmake -S exercises/08-renderer-capstone/project \
  -B build/workspace \
  -DCG_IMPLEMENTATION=workspace \
  -DCG_GPU=off
cmake --build build/workspace
python3 exercises/check.py --impl workspace --stage 01-transform-trace --expect pass --gpu off
```

새 workspace의 공개 미완성 경계를 먼저 확인하려면 `--expect not-implemented`를 사용합니다. reference 비교는 다음 명령이 생성한 좌표·clip trace와 checker report를 기준으로 하며 reference source를 workspace로 복사하지 않습니다.

```sh
python3 exercises/check.py --impl reference --stage 01-transform-trace --expect pass --gpu off
```

자동 증거는 artifact 존재뿐 아니라 identity, direction translation 제외, normal/tangent 직교, hierarchy 순서, clipping 뒤 plane 범위와 finite viewport 값을 검사합니다. starter와 최소 두 known-bad mutation은 성공으로 판정되면 안 됩니다.

사람 검토에서는 다음에 답합니다.

- 첫 잘못된 공간을 어떤 trace field로 찾았습니까?
- singular normal matrix와 invalid camera를 왜 거부하거나 별도 상태로 분류했습니까?
- 과정 규약을 다른 API profile로 옮길 때 정확히 어느 입구 변환이 필요합니까?

정리는 `make clean`으로 `.guide/`, `build/`, `out/`만 제거합니다. 실패 trace는 원인을 기록할 때까지 보존합니다. workspace 복구가 필요하면 기존 디렉터리를 별도 보존·이름 변경한 뒤에만 `./scripts/new-workspace.sh`를 다시 실행합니다.
