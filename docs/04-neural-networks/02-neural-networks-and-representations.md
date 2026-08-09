# 신경망과 표현 학습

신경망은 선형 변환과 비선형 변환을 여러 층 합성해 input에서 task에 유용한 representation을 학습한다. Layer 수보다 **각 representation이 어떤 정보를 보존하고 어떤 inductive bias를 갖는지**가 중요하다.

## 1. Linear layer

```text
h = xW + b
```

Linear layer만 여러 개 쌓아도 전체는 하나의 linear transformation으로 합쳐진다. 비선형 activation이 필요하다.

## 2. Activation

### ReLU

```text
ReLU(z) = max(0, z)
```

계산이 단순하고 널리 사용된다. 음수 영역 gradient가 0이 되어 unit이 지속적으로 비활성화될 수 있다.

### Sigmoid·tanh

출력 범위가 제한되지만 큰 절대값에서 gradient가 작아질 수 있다. Gate나 probability output 등 목적에 맞게 사용한다.

### Smooth activations

GELU, SiLU 같은 activation은 현대 architecture에서 흔하다. 이름보다 output·derivative shape와 수치 비용을 이해한다.

## 3. Multi-layer perceptron

```text
h1 = activation(xW1 + b1)
logits = h1W2 + b2
```

Hidden dimension과 layer 수는 capacity를 정한다. 작은 tabular dataset에서는 강한 tree·linear baseline보다 낫지 않을 수 있다.

## 4. Output와 loss

### Binary classification

- output: logit 하나
- loss: binary cross-entropy with logits
- inference: sigmoid로 score, 별도 threshold

### Multi-class

- output: class 수만큼 logits
- loss: cross-entropy
- label: class index

### Multi-label

- output: label별 logit
- loss: 독립 binary loss 또는 구조적 objective
- threshold: label별 다를 수 있음

### Regression

- output: scalar 또는 vector
- loss: MSE, MAE, quantile 등

Output activation을 loss API가 내부 처리하는지 확인한다. Softmax를 두 번 적용하지 않는다.

## 5. Representation

Hidden vector는 input을 task에 유용한 좌표계로 변환한 것이다. “의미를 이해한다”는 표현 대신 다음을 검증한다.

- downstream prediction에 필요한 정보를 보존하는가
- 같은 label의 sample이 가까운가
- nuisance variation에 덜 민감한가
- new domain에 transfer되는가
- 특정 shortcut을 담고 있지 않은가

Visualization이나 probe는 제한된 증거다.

## 6. Inductive bias

Architecture는 어떤 구조를 쉽게 학습할지 가정한다.

- convolution: local pattern과 translation sharing
- recurrent model: 순차 state
- attention: content-based interaction
- graph network: node-edge 관계
- equivariant model: 특정 transformation 구조

Dataset 크기와 task 구조에 맞는 bias는 sample efficiency를 높일 수 있다.

## 7. Parameter count와 capacity

Parameter가 많으면 표현력이 커질 수 있지만 다음도 함께 변한다.

- memory·compute
- optimization difficulty
- data 요구량
- memorization·privacy 위험
- latency와 artifact size

Parameter count만으로 실제 capacity나 generalization을 판단하지 않는다. Architecture와 training procedure가 중요하다.

## 8. Initialization

모든 weight를 같은 값으로 시작하면 대칭이 깨지지 않아 unit이 같은 update를 받을 수 있다. 초기화는 activation과 fan-in/out에 맞춰 scale을 정한다.

검사:

- 첫 forward의 activation mean·variance
- layer별 gradient norm
- saturation·dead unit
- seed 변화

## 9. Depth와 residual connection

깊은 network는 여러 단계의 representation을 학습할 수 있지만 gradient와 optimization이 어려워진다. Residual connection은 다음 형태다.

```text
h_next = h + F(h)
```

Shape가 같아야 하거나 projection이 필요하다. Residual이 모든 optimization 문제를 해결하지 않는다.

## 10. Normalization

### Batch normalization

Batch 통계를 사용하고 running state를 유지한다. Train과 eval behavior가 다르며 작은 batch·distribution shift에 민감할 수 있다.

### Layer normalization

한 sample의 feature axis를 정규화한다. Sequence model에서 널리 사용된다.

Normalization axis, learned scale·bias와 epsilon을 확인한다.

## 11. Dropout

Train 중 unit을 무작위로 제거하고 scale을 조정한다. Evaluation에서는 비활성화한다.

- train/eval mode 필요
- uncertainty estimator로 사용할 경우 별도 방법론
- 작은 model·dataset에서 효과 validation
- residual·normalization 위치와 상호작용

## 12. Convolution의 핵심

Kernel이 local window를 이동하며 같은 weight를 공유한다.

- receptive field
- stride·padding·dilation
- channel axis
- output shape

Image뿐 아니라 sequence·signal에 사용할 수 있다. Padding이 경계에 어떤 가정을 넣는지 확인한다.

## 13. Recurrent state

RNN류는 순차적으로 hidden state를 갱신한다.

```text
h_t = f(x_t, h_{t-1})
```

Long dependency, vanishing/exploding gradient와 순차 계산 비용이 있다. LSTM·GRU는 gate로 state 흐름을 조절한다. Transformer를 이해하기 위한 역사적 맥락으로 알고, 모든 sequence task에 반드시 구현할 필요는 없다.

## 14. Embedding layer

Discrete ID를 dense vector로 lookup한다.

```text
vocabulary size V
embedding dimension D
weight shape (V, D)
input IDs (B, T)
output (B, T, D)
```

Padding ID, unknown ID, vocabulary version과 freeze/fine-tune 정책이 artifact 계약이다.

## 15. Multi-task learning

한 representation에서 여러 output을 학습할 수 있다.

```text
shared encoder
├── task A head
└── task B head
```

Loss weight, label availability와 task conflict를 확인한다. Auxiliary task가 main task에 실제로 도움되는지 ablation한다.

## 16. Representation collapse와 shortcut

Contrastive·self-supervised 학습에서는 모든 input이 같은 vector가 되는 collapse를 막아야 한다. Supervised에서도 model이 ID나 background shortcut만 학습할 수 있다.

진단:

- representation variance
- nearest neighbor 사례
- feature ablation
- source-shift evaluation
- counterfactual input

## 17. 모델 선택 원칙

신경망을 선택하기 전에 확인한다.

- linear·tree baseline 대비 개선 가능성이 있는가
- raw image·audio·text처럼 learned representation이 필요한가
- data와 compute가 충분한가
- latency·memory·explainability 요구를 만족하는가
- pretrained model을 사용할 수 있는가

Tabular data라는 이유만으로 MLP를 기본 선택하지 않는다.

## 18. 대표적인 실패

### Architecture tourism

여러 최신 layer를 추가하지만 problem·data·metric은 고정되지 않는다.

### Output-loss mismatch

Softmax output에 logits용 loss를 잘못 적용하거나 multi-label을 multi-class로 처리한다.

### Hidden representation을 semantic truth로 해석

2D projection이나 nearest neighbor만으로 의미를 주장한다.

### Bigger is better

Parameter를 늘리고 compute·latency·overfitting·reproducibility 비용을 제외한다.

## 19. 리뷰 질문

- Output와 loss가 task type과 맞는가?
- 각 layer의 input·output shape와 activation이 명확한가?
- Architecture의 inductive bias가 data 구조와 연결되는가?
- Initialization·normalization·residual이 어떤 상태를 만든는가?
- Linear·tree·pretrained baseline과 공정하게 비교했는가?
- Representation이 실제로 보존·제거하는 정보를 어떤 검사로 확인했는가?
- Parameter·latency·memory budget을 지키는가?

## 실습 연결

누적 실습 6단계에서는 feature 수에 비해 작은 MLP를 사용하고, logistic regression baseline과 같은 split·metric에서 비교한다. Architecture 변경보다 tiny-batch overfit, loss·gradient trace와 seed 안정성을 먼저 통과시킨다.
