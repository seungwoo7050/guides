# 보간·원근 보정·미분값

## 목표

coverage를 통과한 sample에서 barycentric coordinate를 계산하고, screen-space에서 선형인 값과 perspective-correct 보간이 필요한 vertex attribute를 구분합니다. depth, UV, color, normal의 보간 계약과 texture LOD에 사용하는 screen derivative를 중간 값으로 검증합니다.

## 시작하기 전에

[삼각형 coverage](06-triangle-setup-coverage-and-fill-rules.md)가 sample 소유권과 signed area를 제공합니다. 각 vertex에는 screen position뿐 아니라 clip-space `w`, view/world position, UV, color, normal 등 필요한 값을 보존합니다.

### barycentric coordinate

triangle vertex `v0, v1, v2`에 대해 sample `p`의 barycentric weight `λ0, λ1, λ2`를 edge function 비율로 구할 수 있습니다.

```text
λ0 + λ1 + λ2 = 1
p = λ0 v0 + λ1 v1 + λ2 v2
```

coverage rule과 weight 계산이 다른 edge convention을 사용하면 경계에서 값이 불연속적일 수 있습니다. 같은 setup 값을 재사용하고, weight sum과 finite 여부를 검사합니다.

### affine interpolation

screen-space에서 선형인 값 `a`는 다음처럼 계산할 수 있습니다.

```text
a = λ0 a0 + λ1 a1 + λ2 a2
```

vertex color처럼 화면 평면에서 의도적으로 선형인 값에는 충분할 수 있습니다. 그러나 3D surface의 UV나 world position은 perspective projection 뒤 screen-space에서 affine하지 않습니다.

### perspective-correct interpolation

각 vertex의 attribute `a_i`와 clip `w_i`를 사용합니다.

```text
q_i = 1 / w_i
numerator   = Σ λ_i (a_i * q_i)
denominator = Σ λ_i q_i
a = numerator / denominator
```

`denominator`가 유한하고 0에서 충분히 떨어져 있는지 검사합니다. clipping이 올바르게 수행됐다면 유효 triangle에서 불안정한 값이 드물어야 하며, 발생하면 primitive id와 vertex `w`를 기록합니다.

원근이 강한 quad에 checker texture를 적용하면 affine UV는 대각선 기준으로 찌그러집니다. 이 fixture는 가장 중요한 알려진 오답입니다.

### depth interpolation

깊이 값은 API convention과 projection에 따라 다릅니다. 과정의 NDC depth는 `[0,1]`입니다. 구현에서 어떤 값을 보간하고 depth attachment에 쓰는지 한 가지 정본을 유지합니다.

- clip `z`와 `w`에서 sample의 NDC depth를 계산
- 또는 setup된 screen-space depth plane을 사용

world-space distance, view-space `z`, clip `z`, NDC depth를 같은 이름 `depth`로 부르지 않습니다. depth test의 값과 linear distance가 필요하면 별도로 재구성하고 fixture를 둡니다.

### normal과 방향 값

normal을 perspective-correct 보간한 뒤 다시 normalize합니다. vertex normal의 선형 조합 길이는 일반적으로 1이 아닙니다. tangent·bitangent도 공간과 handedness를 보존하고, normal mapping에서 TBN basis를 재정규화할 정책을 정합니다.

### flat와 no-perspective 값

GPU shader interface에는 보간하지 않는 flat 값이나 perspective를 적용하지 않는 보간 qualifier가 있을 수 있습니다. software 정본에서도 attribute마다 mode를 명시할 수 있습니다.

- flat: provoking vertex의 값을 그대로 사용
- affine/no-perspective: screen barycentric으로 선형 보간
- perspective: `1/w` 보정

primitive id, material id 같은 정수 값은 flat이어야 합니다.

### screen derivative

texture LOD와 일부 shading 기법에는 `dFdx`, `dFdy`와 같은 screen derivative가 필요합니다. software 정본은 두 경로 중 하나를 선택할 수 있습니다.

1. attribute plane의 analytic derivative
2. 인접 sample 또는 2×2 quad의 finite difference

analytic 방식은 triangle 내부에서 안정적이지만 perspective attribute는 quotient rule이 필요합니다. quad 방식은 GPU 동작과 비슷한 관찰을 제공하지만 triangle edge와 helper invocation의 정의가 추가됩니다. 필수 실습은 LOD를 위한 UV derivative의 수식과 결과를 기록하되 GPU와 bit-identical을 요구하지 않습니다.

### 정밀도와 보간 순서

- weight 합을 강제로 1로 만들기 전에 오차를 기록합니다.
- vertex attribute와 `1/w`를 미리 준비하면 반복 계산을 줄일 수 있습니다.
- 매우 큰 world coordinate를 fragment까지 보간하면 정밀도 문제가 커질 수 있습니다.
- shading 공간을 view 또는 camera-relative world로 선택할 수 있지만 과정 내에서 명시합니다.

## 검증 fixture

- triangle vertex와 centroid의 barycentric 값
- weight sum과 vertex endpoint exactness
- affine와 perspective UV가 크게 다른 tilted quad
- flat primitive id가 triangle 전체에서 동일
- normal interpolation 뒤 normalize 전후 길이
- depth의 near 0, far 1 범위
- UV derivative와 선택 mip level
- `w`가 서로 크게 다른 vertex와 clipping 경계

trace는 한 sample에 대해 `λ`, `1/w`, numerator, denominator와 최종 attribute를 기록합니다.

## 흔한 오답

- 모든 attribute를 affine 보간
- 이미 NDC로 나눈 뒤 원래 `w`를 버림
- integer id를 실수 보간 후 반올림
- normal을 보간하고 normalize하지 않음
- view-space z와 depth buffer 값을 혼용
- derivative를 triangle 밖의 임의 pixel과 비교
- weight 오차를 숨기기 위해 clamp한 뒤 원인 추적 불가

## 연결 실습

- [`04-perspective-depth-blend`](../../exercises/04-perspective-depth-blend/README.md): affine/perspective 차이와 depth 값을 pixel trace로 비교합니다.
- [`05-textured-lit-scene`](../../exercises/05-textured-lit-scene/README.md): UV derivative, normal과 world/view position을 texture·lighting에 연결합니다.

## 완료 기준

- barycentric weight와 coverage setup을 같은 convention으로 계산합니다.
- attribute별 flat·affine·perspective mode를 구분합니다.
- `1/w` 보정의 중간 값을 trace하고 tilted surface에서 오답을 재현합니다.
- depth·normal·UV derivative의 공간과 범위를 명시하고 유효성을 검사합니다.
