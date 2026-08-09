# 좌표 공간과 변환

## 목표

vertex와 방향 벡터가 어느 좌표 공간에 있는지 명시하고, `local → world → view → clip → NDC → viewport` 전이를 값과 trace로 검증합니다. 행렬 저장 방식, 벡터 표기, handedness와 곱셈 순서를 API마다 추측하지 않고 과정 규약으로 고정합니다.

## 시작하기 전에

일반 선형대수의 증명이나 C++ 수학 타입 설계 전체는 범위 밖입니다. 여기서는 그래픽스 pipeline에 필요한 다음 연산을 사용할 수 있어야 합니다.

- vector 덧셈, scalar 곱, dot, cross, 길이와 normalize
- 4×4 matrix와 homogeneous coordinate
- translation, rotation, scale의 합성
- matrix inverse와 transpose의 의미

과정 규약은 [로드맵](../00-roadmap.md)의 표를 정본으로 사용합니다.

```text
p_clip = P * V * M * p_local
p_ndc  = p_clip.xyz / p_clip.w
p_viewport = viewport(p_ndc)
```

### 공간을 타입과 이름에 드러내기

모든 값이 `Vec3`이면 잘못된 공간을 compiler가 거부하지 못합니다. 반드시 강한 타입을 구현할 필요는 없지만 이름과 API 경계에는 공간을 드러냅니다.

```text
LocalPosition
WorldPosition
ViewDirection
ClipPosition
NdcPosition
ScreenPoint
```

다음 연산은 의미가 다릅니다.

- position에는 translation이 적용됩니다.
- direction에는 translation이 적용되지 않습니다.
- normal은 비균일 scale이 있을 때 model matrix 그대로 변환하지 않습니다.
- clip position은 perspective divide 이전이므로 `w`를 보존해야 합니다.

### homogeneous coordinate

position은 `(x, y, z, 1)`, direction은 `(x, y, z, 0)`으로 확장합니다. 이 차이는 translation의 적용 여부를 행렬 곱에 포함합니다. 그러나 normal을 단순한 direction으로만 보면 부족합니다. normal은 표면 tangent와 수직 관계를 보존해야 하므로 비균일 scale에서는 model matrix의 inverse transpose를 사용합니다.

```text
n_world = normalize(transpose(inverse(M3x3)) * n_local)
```

행렬이 singular이면 inverse가 존재하지 않습니다. scale 축이 0인 object를 어떻게 처리할지 정합니다.

- asset/scene validation에서 거부
- object를 renderable하지 않은 상태로 표시
- 명시적 fallback normal 사용

조용히 identity로 대체하지 않습니다.

### handedness와 cross product

left-handed/right-handed라는 이름만으로 모든 행렬의 부호를 결정할 수 없습니다. 다음을 함께 기록해야 합니다.

- camera forward 축
- view matrix 구성
- projection의 clip depth 범위
- viewport의 Y 방향
- front-face winding을 판정하는 공간

과정은 camera가 `+Z`를 바라보는 left-handed world/view를 사용합니다. viewport는 top-left origin과 `+Y down`을 사용하므로 NDC에서 viewport로 옮길 때 Y mapping을 명시합니다.

```text
x_screen = viewport_x + (x_ndc * 0.5 + 0.5) * width
y_screen = viewport_y + (1.0 - (y_ndc * 0.5 + 0.5)) * height
```

실제 SDL3 GPU backend의 좌표 보정은 API가 처리할 수 있지만, CPU 정본과 shader 입력은 이 규약을 기준으로 비교합니다.

### 변환 순서

`T * R * S * p`와 `S * R * T * p`는 같지 않습니다. object가 자신의 원점에서 scale·rotation된 뒤 world로 이동하려면 column vector 규약에서 보통 `M = T * R * S`를 사용합니다. scene hierarchy에서는 parent world와 child local을 합성합니다.

```text
M_child_world = M_parent_world * M_child_local
```

순환 parent 참조는 행렬 문제가 아니라 scene graph validation 문제입니다.

## 검증 fixture

최소한 다음 장면을 갖습니다.

1. identity에서 점과 방향이 변하지 않음
2. translation이 position에는 적용되고 direction에는 적용되지 않음
3. 90도 회전의 basis vector 결과
4. 비균일 scale 뒤 normal과 tangent의 dot가 0에 가까움
5. parent translation + child rotation 합성
6. `w = 0`, 매우 작은 `w`, 음수 `w`를 가진 clip position의 거부 또는 다음 단계 전달
7. viewport corner와 center mapping

trace에는 각 matrix와 단계별 값, 유효성 판정을 함께 기록합니다. 최종 screen 좌표만 저장하면 어느 행렬에서 틀렸는지 찾을 수 없습니다.

## 흔한 오답

- row-major memory layout과 row-vector 수학 규약을 같은 개념으로 취급
- projection matrix를 두 번 transpose
- NDC에 도달하기 전에 `w`를 버림
- direction에 translation 적용
- normal에 model matrix를 그대로 적용
- viewport Y flip을 asset 또는 shader 여러 곳에서 중복 수행
- front-face winding을 clip space와 viewport space에서 혼용

## 연결 실습

- [`01-transform-trace`](../../exercises/01-transform-trace/README.md): 정해진 scene의 단계별 좌표와 행렬을 JSON으로 기록합니다.
- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): normal matrix와 object hierarchy를 조명 결과에 연결합니다.

## 완료 기준

- 하나의 vertex와 normal을 local에서 viewport까지 수치로 추적합니다.
- matrix 저장 layout, 벡터 표기와 곱셈 순서를 서로 다른 개념으로 설명합니다.
- 비균일 scale에서 normal matrix가 필요한 이유를 tangent와의 수직성으로 검증합니다.
- viewport origin·Y 방향·front-face 규약을 코드와 artifact에서 한 번만 변환합니다.
