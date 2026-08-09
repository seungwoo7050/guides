# Tensor, autodiff와 계산 그래프

신경망 프레임워크를 읽으려면 layer 이름보다 **tensor의 shape·dtype·device와 gradient가 흐르는 계산 그래프**를 먼저 이해해야 한다. 코드가 실행된다는 사실은 의도한 축과 gradient가 맞다는 증거가 아니다.

## 1. Tensor 계약

Tensor마다 최소 네 가지를 기록한다.

```text
shape
axis meaning
dtype
device
```

예:

```text
input_ids:       (batch, sequence)      int64, CPU/GPU
attention_mask:  (batch, sequence)      bool
embeddings:      (batch, sequence, dim) float32
logits:          (batch, classes)       float32
labels:          (batch,)               int64
```

같은 shape라도 axis 의미가 다르면 다른 값이다. `(batch, time, channel)`과 `(batch, channel, time)`을 명시한다.

## 2. Dtype

### Integer

ID, index와 class label에 사용한다. Embedding lookup과 cross-entropy label은 보통 정수 index를 기대한다.

### Floating point

- float64: 높은 정밀도, 더 큰 memory·낮은 accelerator throughput
- float32: 일반적인 기준
- float16·bfloat16: memory와 throughput 절약, 안정성 관리 필요

### Boolean

Mask와 조건에 사용한다. 0/1 float mask와 broadcasting 의미가 다를 수 있다.

Dtype conversion은 memory, precision과 gradient에 영향을 준다. Input pipeline에서 암묵적으로 바뀌지 않게 한다.

## 3. Device

Tensor와 model parameter가 같은 device에 있어야 operation을 실행할 수 있다. Device 이동은 copy와 synchronization을 만들 수 있다.

```text
CPU에서 load·preprocess
→ accelerator로 batch 이동
→ model forward/backward
→ 필요한 scalar만 CPU로 기록
```

Loop 안에서 작은 tensor를 반복 이동하거나 item을 읽으면 accelerator synchronization이 생길 수 있다. 필수 실습은 CPU에서 먼저 정확성을 검증한다.

## 4. View, reshape와 contiguous memory

Tensor는 같은 storage를 다른 shape로 보는 view일 수 있다.

- reshape가 copy인지 view인지 library와 layout에 따라 달라질 수 있음
- transpose 뒤 memory가 contiguous하지 않을 수 있음
- in-place update가 공유 storage에 영향을 줄 수 있음

Model correctness는 memory layout에 의존하지 않게 만들고, 성능 최적화 전 shape·alias를 이해한다.

## 5. Broadcasting

차원이 1이거나 빠진 axis를 확장해 element-wise 연산한다.

예:

```text
X: (B, D)
b: (D,)
X + b: (B, D)
```

위험:

- batch와 feature 크기가 우연히 같아 잘못된 axis가 통과
- mask shape가 `(B,)`인데 `(B, T)`에 의도와 다르게 적용
- loss weight가 class가 아니라 sample axis에 broadcast

핵심 경계에서 shape assertion과 작은 손계산 fixture를 둔다.

## 6. Computation graph

Forward operation을 node와 edge로 기록한다.

```text
x ── matmul ── z ── activation ── h ── loss
w ───────┘
```

Autodiff는 graph를 역순으로 따라 chain rule을 적용한다. Graph는 tensor 값뿐 아니라 어떤 operation이 어떤 parameter와 연결됐는지를 나타낸다.

## 7. Leaf와 gradient

학습 parameter는 보통 gradient를 저장하는 leaf tensor다. Forward 중간 결과도 gradient 계산에 필요할 수 있지만 `.grad`가 자동으로 보존되지 않을 수 있다.

확인:

- 어떤 parameter에 gradient가 필요한가
- 어떤 input까지 gradient가 필요한가
- gradient accumulation을 언제 0으로 초기화하는가
- frozen parameter가 optimizer에 포함되는가

## 8. Backward와 scalar loss

Scalar loss에서 backward를 호출하면 각 parameter에 대한 gradient를 계산한다. Vector output이라면 vector-Jacobian product와 upstream gradient가 필요하다.

Loss reduction을 확인한다.

```text
sum: batch 크기에 비례해 gradient scale 증가
mean: batch 평균으로 scale 유지
```

Batch size를 바꾸며 learning rate를 비교할 때 중요하다.

## 9. Gradient accumulation

많은 프레임워크는 backward를 여러 번 호출하면 gradient를 더한다.

기본 loop:

```text
zero gradients
→ forward
→ loss
→ backward
→ optimizer step
```

Micro-batch accumulation을 의도하면 여러 backward 뒤 한 번 step한다. Loss scaling과 마지막 작은 batch를 고려한다.

## 10. detach와 no-grad

### detach

현재 tensor 값을 graph에서 분리한다. 잘못 사용하면 필요한 gradient가 끊긴다.

### no-grad·inference mode

평가·inference에서 graph 생성을 막아 memory와 비용을 줄인다. Model의 train/eval mode와 별개다.

```text
model.eval()        dropout·normalization behavior 변경
no_grad()           gradient graph 비활성화
```

둘을 모두 필요한 위치에 사용한다.

## 11. In-place operation

값을 직접 바꾸면 graph가 backward에 필요한 이전 값을 잃거나 alias를 통해 다른 tensor를 바꿀 수 있다. 프레임워크가 오류를 내기도 하지만 모든 의미 오류를 잡지는 못한다.

초기 학습 코드에서는 명확한 out-of-place operation을 우선한다.

## 12. Automatic differentiation의 한계

Autodiff는 작성한 operation의 derivative를 계산한다. 다음은 확인하지 않는다.

- loss가 실제 목표에 맞는가
- label과 class axis가 맞는가
- reduction이 의도한 것인가
- data leakage가 있는가
- gradient가 유용한 scale인가
- non-differentiable decision을 올바르게 근사했는가

## 13. Gradient check

작은 deterministic 함수에서 finite difference와 비교한다.

```text
g_numeric = [L(θ+ε) - L(θ-ε)] / (2ε)
g_auto    = autodiff gradient
relative error 비교
```

주의:

- dropout·random augmentation 비활성화
- float64와 작은 model 사용 고려
- kink가 있는 activation 지점 피하기
- 여러 epsilon 확인

전체 대형 model을 check하지 않고 custom operation과 loss의 작은 입력을 검사한다.

## 14. Mask

Sequence padding, future token 차단과 missing value를 mask로 표현한다.

확인:

- `True`가 허용인지 차단인지 API 의미
- mask axis와 broadcast
- padding token이 loss에 포함되는지
- 모든 position이 masked된 row 처리
- `-inf`와 low-precision softmax 안정성

Mask 오류는 shape가 맞아 조용히 잘못 학습하기 쉽다.

## 15. Reduction axis

Softmax, mean, normalization과 loss가 어느 axis를 줄이는지 명시한다.

예:

```text
logits: (B, T, V)
softmax axis: V
loss mask: T
batch reduction: B와 valid token
```

Vocabulary 대신 time axis에 softmax를 적용해도 shape가 유지될 수 있다. 작은 fixture로 probability sum axis를 검사한다.

## 16. Numerical stability

- stable softmax와 log-sum-exp
- loss 내부에서 sigmoid 후 log를 따로 계산하지 않고 logits 기반 API 사용
- gradient explosion·underflow
- mixed precision scaling
- epsilon 위치

NaN을 0으로 바꾸고 계속 학습하지 않는다. 최초 비정상 operation과 입력을 찾는다.

## 17. 대표적인 실패

### Loss는 줄지만 label axis가 틀림

Broadcasting으로 다른 sample label이 섞여도 평균 loss가 변화할 수 있다.

### Evaluation에 graph 생성

메모리가 누적되고 성능이 저하된다.

### Gradient를 초기화하지 않음

의도치 않은 accumulation으로 update가 달라진다.

### detach로 학습 차단

Logging이나 numpy 변환을 위해 중간 representation을 detach한 뒤 그 값을 loss에 재사용한다.

### train/eval mode 혼동

Validation에서도 dropout·batch normalization이 train behavior로 동작한다.

## 18. 리뷰 질문

- 모든 주요 tensor의 shape·axis·dtype·device가 문서화됐는가?
- Loss reduction과 mask denominator가 정확한가?
- Gradient가 필요한 parameter와 frozen parameter를 구분했는가?
- Zero-grad·backward·step 순서가 의도한 accumulation과 맞는가?
- Evaluation에서 `eval` mode와 no-grad를 모두 적용하는가?
- Custom operation·loss를 작은 gradient check로 검증했는가?
- NaN·inf가 발생한 최초 경계를 찾을 수 있는가?

## 실습 연결

누적 실습 6단계에서는 batch, feature, hidden, class axis를 training report에 기록하고, 첫 batch의 logits·label·loss shape와 gradient norm을 fixture로 남긴다.
