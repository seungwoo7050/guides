# 필요한 수학과 수치 계약

이 문서는 선형대수·미적분·확률론 전체를 가르치지 않는다. 모델 코드를 읽고 shape, loss와 gradient를 검증하는 데 필요한 최소 언어를 제공한다. 수식은 구현과 평가 계약을 더 정확히 표현하기 위한 도구다.

## 1. Scalar, vector, matrix, tensor

- scalar: 하나의 수 `a`
- vector: 순서 있는 수의 목록 `x ∈ R^d`
- matrix: 2차원 배열 `X ∈ R^{n×d}`
- tensor: 3차원 이상의 일반화된 배열

Tabular batch를 다음처럼 둔다.

```text
n = sample 수
d = feature 수
X shape = (n, d)
y shape = (n,)
```

신경망 코드에서 가장 먼저 확인할 것은 수식 이름보다 shape다.

```text
입력 batch B × feature D
weight D × hidden H
출력 B × hidden H
```

Shape가 맞는다고 의미가 맞는 것은 아니다. axis가 sample, time, channel 중 무엇인지 기록한다.

## 2. Vector operation

### Dot product

```text
w · x = Σ_i w_i x_i
```

선형 모델의 score는 feature의 가중합이다. 각 항의 단위와 scaling이 coefficient 해석에 영향을 준다.

### Matrix multiplication

```text
Z = XW
```

여러 sample과 여러 output을 한 번에 계산한다. element-wise multiplication `X * W`와 구분한다.

### Norm

```text
L1: ||w||_1 = Σ_i |w_i|
L2: ||w||_2 = sqrt(Σ_i w_i^2)
```

Regularization, 거리와 gradient clipping에서 사용한다. 같은 “크기”라도 목적과 geometry가 다르다.

## 3. 평균, 분산과 표준화

```text
mean μ = (1/n) Σ_i x_i
variance σ² = (1/n) Σ_i (x_i - μ)²
standard score z = (x - μ) / σ
```

Train mean과 variance로 validation/test를 transform한다. 전체 dataset 통계를 사용하면 preprocessing leakage가 생긴다.

분산이 0이거나 매우 작은 feature는 division을 불안정하게 만들 수 있다. 구현은 epsilon, constant feature 처리와 dtype를 명시해야 한다.

## 4. 확률과 조건부 확률

```text
P(Y=1 | X=x)
```

입력 `x`가 주어졌을 때 outcome이 positive일 조건부 확률이다. 모델 score가 자동으로 잘 calibrated된 probability인 것은 아니다.

### Expectation

확률 변수의 평균적 값을 나타낸다.

```text
E[L(Y, f(X))]
```

모델이 미래 분포에서 기대하는 loss를 population risk라고 볼 수 있다. 실제로는 유한한 dataset 평균인 empirical risk를 최소화한다.

### Independence

두 사건이 독립이라는 가정은 강하다. Random split은 row가 대략 독립이고 같은 분포에서 왔다는 가정을 자주 암묵적으로 사용한다.

## 5. Likelihood와 log

독립 sample의 likelihood는 probability의 곱이다.

```text
L(θ) = Π_i P(y_i | x_i; θ)
```

작은 수를 계속 곱하면 underflow가 생긴다. Log를 취하면 곱이 합으로 바뀐다.

```text
log L(θ) = Σ_i log P(y_i | x_i; θ)
```

Negative log likelihood를 최소화하는 형태가 흔하다. `log(0)`을 피하기 위한 clipping이 metric 의미를 바꿀 수 있으므로 epsilon을 기록한다.

## 6. Sigmoid와 softmax

### Sigmoid

```text
σ(z) = 1 / (1 + exp(-z))
```

실수 score를 0과 1 사이로 바꾼다. 큰 양·음수에서 naive `exp` 계산은 overflow될 수 있다.

### Softmax

```text
softmax(z_i) = exp(z_i) / Σ_j exp(z_j)
```

수치 안정성을 위해 최대값을 뺀다.

```text
softmax(z_i) = exp(z_i - m) / Σ_j exp(z_j - m)
m = max_j z_j
```

모든 logit에 같은 상수를 더해도 결과가 같다는 성질을 사용한다.

## 7. Derivative와 gradient

Derivative는 작은 입력 변화에 대한 출력 변화율이다.

```text
df/dx
```

Parameter가 여러 개면 각 parameter에 대한 편미분을 모은 gradient를 사용한다.

```text
∇_θ L = [∂L/∂θ_1, ..., ∂L/∂θ_k]
```

Gradient descent의 기본 update:

```text
θ_next = θ - η ∇_θ L
```

`η`는 learning rate다. Gradient는 “정답으로 가는 방향”이 아니라 현재 지점에서 loss가 가장 빠르게 증가하는 국소 방향이다. Non-convex objective에서는 local geometry와 optimizer state가 결과에 영향을 준다.

## 8. Chain rule과 backpropagation

함수가 합성돼 있을 때 derivative를 연결한다.

```text
y = f(g(x))
dy/dx = df/dg × dg/dx
```

신경망은 layer의 합성이다. Backpropagation은 계산 그래프를 역순으로 따라 local derivative를 곱·합해 parameter gradient를 계산한다.

Autodiff가 수학적 의미를 대신하지 않는다. `requires_grad`, detach, in-place operation과 reduction shape를 잘못 쓰면 코드가 실행돼도 의도한 gradient가 아닐 수 있다.

## 9. Finite difference gradient check

작은 모델에서는 수치 미분과 analytic/autodiff gradient를 비교할 수 있다.

```text
df/dx ≈ [f(x + ε) - f(x - ε)] / (2ε)
```

`ε`가 너무 크면 근사 오차, 너무 작으면 floating-point cancellation이 커진다. 여러 epsilon에서 상대 오차를 본다.

[`examples/gradient_check.py`](../../examples/gradient_check.py)는 scalar linear regression loss에서 analytic gradient와 finite difference를 비교한다.

## 10. Floating-point

실수 연산은 유한 정밀도의 근사다.

- 덧셈 순서에 따라 마지막 bit가 달라질 수 있다.
- 매우 큰 값과 작은 값을 더하면 작은 값이 사라질 수 있다.
- `NaN`, `inf`, underflow와 overflow가 전파된다.
- CPU, GPU, library kernel과 병렬 reduction이 다른 결과를 낼 수 있다.

따라서 exact equality보다 허용 오차를 사용하고, dtype와 device를 artifact·실험 기록에 남긴다.

## 11. Broadcasting

크기가 다른 tensor를 규칙에 따라 확장해 element-wise 연산한다. 편리하지만 axis 오류를 숨긴다.

예:

```text
X shape: (batch, feature)
b shape: (feature,)
X + b  # 각 row에 b를 더함
```

`b`가 `(batch,)`인데 우연히 batch와 feature 크기가 같으면 잘못된 axis가 통과할 수 있다. 핵심 경계에서 shape assertion과 named description을 사용한다.

## 12. Distance와 similarity

### Euclidean distance

```text
||x - y||_2
```

Scale이 큰 feature가 거리를 지배한다. KNN·clustering 전에 scaling과 metric 의미를 검토한다.

### Cosine similarity

```text
cos(x, y) = (x · y) / (||x|| ||y||)
```

방향 유사성을 본다. Zero vector 처리와 embedding normalization 여부를 명시한다.

Distance가 의미 있으려면 representation이 그 geometry를 보존해야 한다.

## 13. Entropy와 cross-entropy의 직관

Binary cross-entropy:

```text
-[y log p + (1-y) log(1-p)]
```

정답 class에 낮은 probability를 주면 큰 벌점을 준다. 0/1 분류 정확도와 달리 confidence를 사용한다.

Loss를 줄이는 것이 실제 action cost를 직접 줄인다는 뜻은 아니다. Training objective와 business metric을 분리한다.

## 14. 수식 검토 절차

1. 각 기호의 의미와 단위를 적는다.
2. 입력·출력 shape를 적는다.
3. sample axis와 feature/time/class axis를 구분한다.
4. reduction이 sum인지 mean인지 확인한다.
5. 극단값·zero·empty batch를 넣어 본다.
6. 작은 손계산 또는 기준 구현과 비교한다.
7. gradient는 finite difference로 점검한다.
8. dtype·device와 tolerance를 기록한다.

## 15. 범위 밖

- 선형대수의 고유값·SVD 증명 전체
- 확률 측도론과 통계 추론 전문 과정
- convex optimization의 수렴 증명
- numerical linear algebra와 GPU kernel 최적화

필요한 프로젝트에서 이론적 깊이가 요구되면 전문 자료로 확장한다. 이 가이드는 수식을 읽지 않고 프레임워크 호출만 조합하는 상태를 벗어나는 데 필요한 기준선을 제공한다.
