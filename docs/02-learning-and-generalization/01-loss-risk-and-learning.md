# Loss, risk와 학습

학습은 dataset에서 정답을 외우는 일이 아니라 **parameter를 바꿔 정해진 objective를 줄이는 절차**다. Objective, 평가 metric과 실제 의사결정 비용을 구분해야 모델이 무엇을 최적화했고 무엇을 보장하지 않는지 설명할 수 있다.

## 1. Hypothesis와 parameter

모델 family를 함수 집합으로 생각할 수 있다.

```text
f_θ(x)
```

- `x`: 입력 feature
- `θ`: 학습할 parameter
- `f`: model architecture 또는 hypothesis family

선형 모델은 weight와 bias를, tree는 split과 leaf 값을, 신경망은 여러 layer의 weight를 학습한다. Model family를 선택하는 순간 표현할 수 있는 함수와 inductive bias가 정해진다.

## 2. Loss

한 sample의 prediction이 label과 얼마나 다른지 수치화한다.

### Regression

Squared error:

```text
L(y, ŷ) = (y - ŷ)^2
```

큰 오류를 강하게 벌한다.

Absolute error:

```text
L(y, ŷ) = |y - ŷ|
```

Outlier 영향이 상대적으로 작지만 0에서 미분 가능성 처리가 필요하다.

### Classification

Binary cross-entropy:

```text
L(y, p) = -[y log p + (1-y) log(1-p)]
```

정답 class에 낮은 probability를 줄수록 크게 벌한다. 0/1 accuracy와 달리 confidence를 사용한다.

Loss는 모델 학습을 위한 수학적 대리 목표다. 실제 false negative 비용이나 사람 검토 시간과 같지 않을 수 있다.

## 3. Empirical risk

알 수 없는 실제 분포의 기대 loss를 population risk라 한다.

```text
R(θ) = E[L(Y, f_θ(X))]
```

실제 분포를 직접 계산할 수 없으므로 train sample 평균을 사용한다.

```text
R_train(θ) = (1/n) Σ_i L(y_i, f_θ(x_i))
```

학습은 대개 empirical risk를 줄인다. Train loss가 낮아졌다는 사실은 같은 분포의 새 sample에서 loss가 낮다는 보장이 아니다. Generalization을 validation과 test에서 확인해야 한다.

## 4. Objective

실제 학습 objective에는 여러 항이 들어갈 수 있다.

```text
objective = data_loss
          + λ * regularization
          + auxiliary_loss
```

- data loss: label과 prediction의 차이
- regularization: parameter 크기나 모델 복잡도 제한
- auxiliary loss: representation 또는 여러 task를 돕는 추가 목표

각 항의 scale을 기록한다. Data loss가 batch mean인지 sum인지에 따라 regularization weight와 learning rate의 의미가 달라진다.

## 5. Objective와 metric을 분리한다

다음은 서로 다를 수 있다.

```text
학습 objective: cross-entropy
선택 metric: average precision
결정 metric: recall at review capacity
제품 metric: 유지율 또는 처리 비용
```

Accuracy를 직접 미분하기 어렵기 때문에 cross-entropy를 학습할 수 있다. 하지만 cross-entropy 개선이 action cost 개선으로 자동 이어지지는 않는다.

Model report에는 다음을 명시한다.

- 어떤 objective를 최적화했는가
- 어떤 metric으로 model을 선택했는가
- 어떤 threshold와 비용으로 action을 정했는가
- 실제 제품 outcome은 무엇으로 확인할 것인가

## 6. Optimization

Parameter update의 기본 형태:

```text
θ_{t+1} = θ_t - η g_t
```

`g_t`는 현재 batch에서 계산한 gradient, `η`는 learning rate다.

### Full batch

전체 train dataset으로 한 번의 gradient를 계산한다. 안정적이지만 큰 dataset에서는 비용이 크다.

### Stochastic·mini-batch

한 sample 또는 작은 batch로 근사 gradient를 계산한다. Noise가 있지만 계산 효율과 일반화에 도움이 될 수 있다.

### Epoch와 step

- step: 한 batch로 update 한 번
- epoch: train sample을 대략 한 번 모두 사용

Data loader의 drop, shuffle, replacement 정책에 따라 정확한 의미가 달라질 수 있다.

## 7. Learning rate

너무 크면 loss가 진동하거나 발산하고, 너무 작으면 학습이 매우 느리거나 좋지 않은 지점에 머문다.

확인할 증거:

- step별 train loss
- validation metric
- gradient norm
- parameter update 크기
- NaN·inf 발생 시점

Scheduler는 문제를 자동 해결하지 않는다. 초기 learning rate, warmup, decay와 total step을 하나의 실험 configuration으로 기록한다.

## 8. Convex와 non-convex

선형 회귀 같은 일부 objective는 convex여서 global optimum 분석이 비교적 쉽다. Deep neural network는 일반적으로 non-convex다.

Non-convex에서 중요한 점:

- initialization과 data order가 결과에 영향을 준다.
- 같은 metric을 만드는 여러 parameter 상태가 존재한다.
- train loss가 낮아도 representation과 calibration이 다를 수 있다.
- optimizer가 찾은 해가 유일한 “정답 모델”은 아니다.

## 9. Supervised, unsupervised, self-supervised

### Supervised learning

명시적인 label `y`를 사용한다.

- classification
- regression
- ranking
- structured prediction

### Unsupervised learning

Label 없이 구조나 representation을 찾는다.

- clustering
- dimensionality reduction
- density estimation
- anomaly detection

“정답이 없다”는 이유로 평가가 필요 없는 것은 아니다. Stability, downstream utility와 domain review가 필요하다.

### Self-supervised learning

원본 데이터에서 학습 target을 만든다.

- 가려진 token 예측
- 다음 token 예측
- 변형된 view 사이의 일치

Pretraining objective와 실제 downstream task가 다르므로 transfer 평가가 필요하다.

### Semi-supervised learning

적은 labeled data와 많은 unlabeled data를 함께 사용한다. Pseudo-label의 오류가 증폭될 수 있으므로 confidence와 validation 경계를 분리한다.

## 10. Parameter와 hyperparameter

- parameter: 학습 과정이 data로 조정하는 값
- hyperparameter: 학습 전에 선택하거나 외부 탐색으로 정하는 값

예:

```text
parameter: linear weight, neural network weight
hyperparameter: regularization strength, tree depth, learning rate, batch size
```

Hyperparameter도 validation data에 맞춰진다. 많은 시도를 할수록 validation overfitting 가능성이 커진다.

## 11. Regularization as preference

Objective에 제약이나 penalty를 넣어 여러 train solution 중 특정 해를 선호한다.

- L1·L2 penalty
- depth·leaf size 제한
- dropout
- data augmentation
- early stopping

Regularization은 “과적합 방지 버튼”이 아니다. 어떤 변화에 불변이어야 하는지, 어떤 모델 복잡도를 선호하는지에 대한 가정이다.

## 12. Class weight와 sampling

Imbalanced class에서 positive loss를 더 크게 가중하거나 sample 비율을 바꿀 수 있다.

주의:

- ranking과 decision threshold에 다른 영향을 준다.
- sampling prevalence가 probability calibration을 바꿀 수 있다.
- validation/test는 목표 환경 분포를 유지해야 한다.
- weight는 실제 cost와 같은 단위가 아닐 수 있다.

먼저 metric과 threshold를 설계하고, class weight를 hyperparameter로 검증한다.

## 13. Label smoothing와 auxiliary objective

현대 모델은 label smoothing, contrastive loss, masked objective 등 여러 학습 목표를 사용한다. 각 목표가 유도하는 behavior를 확인한다.

예를 들어 label smoothing은 극단적인 confidence를 줄일 수 있지만, calibration이나 rare class에 미치는 영향은 별도 평가가 필요하다.

## 14. 학습 로그의 최소 단위

각 run에 다음을 기록한다.

```text
run_id
code revision
train/validation dataset version
split manifest version
model configuration
objective와 reduction
optimizer·learning rate schedule
seed·device·dtype
step·epoch별 train loss
validation metric
checkpoint 선택 기준
종료 이유
```

최고 score만 남기면 실패를 재현할 수 없다.

## 15. 대표적인 실패

### Train objective를 제품 목표로 해석

Cross-entropy 감소를 실제 비용 감소로 주장한다.

### Mean/sum 혼동

Batch size를 바꿨는데 loss scale과 regularization, learning rate를 그대로 비교한다.

### Optimization failure를 model limit로 오인

Learning rate나 label 오류로 학습이 안 됐는데 architecture가 약하다고 결론낸다.

### Validation metric을 objective에 계속 반영

수많은 실험으로 validation에 적응하고도 독립된 final test 없이 일반화 주장을 한다.

## 16. 리뷰 질문

- Model family가 어떤 함수를 표현하고 어떤 가정을 내장하는가?
- Loss와 실제 metric이 어떻게 다르며 왜 이 loss를 선택했는가?
- Objective의 각 항과 reduction scale은 무엇인가?
- Batch, epoch, step의 정확한 의미가 무엇인가?
- Optimization이 충분히 작동했다는 증거가 있는가?
- Class weight·sampling이 calibration과 prevalence에 미치는 영향을 확인했는가?
- Run의 입력과 종료 이유를 재현할 수 있는가?

## 실습 연결

누적 실습 4·6단계에서는 classical model과 neural model이 서로 다른 objective를 사용할 수 있지만 같은 validation·test 계약에서 비교한다. 보고서에는 objective와 선택 metric을 별도 field로 기록한다.
