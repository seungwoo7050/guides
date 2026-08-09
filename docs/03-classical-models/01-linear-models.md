# 선형 모델

선형 모델은 단순해서 버리는 baseline이 아니다. Feature·target·regularization·probability 계약을 드러내고, 복잡한 모델의 이득을 검증하는 강한 기준선이다.

## 1. 선형 회귀

```text
ŷ = w · x + b
```

각 feature가 한 단위 변할 때 다른 feature가 고정됐다는 조건에서 prediction이 얼마나 변하는지 coefficient로 표현한다.

기본 가정과 주의:

- 관계가 feature representation에서 선형적이다.
- Error가 독립이라는 가정은 반복 entity·time data에서 깨질 수 있다.
- Outlier가 squared loss를 지배할 수 있다.
- Correlated feature가 coefficient를 불안정하게 만든다.
- 좋은 prediction이 causal 해석을 보장하지 않는다.

## 2. Feature transformation

원래 변수에 대해 비선형 관계여도 변환 뒤 선형 모델을 사용할 수 있다.

```text
x, x²
log(x)
interaction x1 * x2
one-hot category
spline 또는 basis expansion
```

Model은 transformed feature에 대해 선형이다. Feature 수가 늘면 overfitting과 해석 비용도 커진다. Transformation은 train pipeline 안에서 versioning한다.

## 3. Logistic regression

Binary classification score:

```text
z = w · x + b
p = sigmoid(z)
```

Cross-entropy로 parameter를 학습한다. 이름에 regression이 들어가지만 class probability 또는 log-odds를 모델링한다.

Log-odds:

```text
log[p / (1-p)] = w · x + b
```

Coefficient는 feature 한 단위 변화에 따른 log-odds 변화다. Scale, interaction, regularization과 correlated feature를 고려하지 않고 직접적인 원인 효과로 해석하지 않는다.

## 4. Multi-class

One-vs-rest 또는 multinomial softmax를 사용할 수 있다.

```text
P(y=k|x) = softmax(Wx + b)_k
```

Class가 서로 배타적인지, multi-label인지 구분한다. 한 sample이 여러 label을 가질 수 있다면 독립 sigmoid 또는 구조화된 방법이 필요할 수 있다.

## 5. Scaling

L1·L2 regularization과 gradient optimization은 feature scale에 민감하다.

```text
age: 0~100
revenue: 0~1,000,000
```

같은 regularization strength에서 큰 단위 feature가 다르게 취급될 수 있다. Train 통계로 standardization하고 validation/test에 적용한다.

Binary one-hot feature와 continuous feature를 무조건 같은 방식으로 scaling할 필요는 없다. Pipeline에서 column별 의미를 유지한다.

## 6. Regularization

### Ridge·L2

```text
loss + λ Σ_j w_j²
```

큰 weight를 부드럽게 줄인다. Correlated feature 사이에 weight를 분산할 수 있다.

### Lasso·L1

```text
loss + λ Σ_j |w_j|
```

일부 weight를 0으로 만들 수 있다. “자동 feature selection” 결과가 seed·sample 변화에서 안정적인지 확인한다.

### Elastic net

L1과 L2를 결합한다. Hyperparameter는 validation에서 선택한다.

Regularization strength가 커질수록 단순한 해를 선호하지만 underfitting 가능성이 커진다.

## 7. Intercept와 centering

Intercept는 모든 feature가 0일 때의 prediction이다. Feature 0이 실제 의미를 갖지 않으면 intercept의 도메인 해석은 제한적이다.

Centering은 coefficient와 optimization을 안정화할 수 있다. Sparse one-hot matrix에서는 centering이 dense matrix를 만들 수 있으므로 구현 비용을 확인한다.

## 8. Missing value와 category

Linear model은 raw missing value나 문자열 category를 직접 처리하지 못하는 경우가 많다.

- numeric imputation
- missing indicator
- one-hot encoding
- unknown category 처리
- rare category grouping

이 변환은 train에서 fit한다. 전체 dataset category를 먼저 수집하면 evaluation 정보가 preprocessing에 들어갈 수 있다.

## 9. Multicollinearity

서로 강하게 correlated된 feature는 비슷한 정보를 제공한다.

영향:

- coefficient 부호와 크기가 sample에 따라 크게 변함
- 개별 coefficient의 해석 불안정
- prediction은 여전히 안정적일 수 있음

대응:

- domain 기준으로 중복 feature 제거
- regularization
- coefficient stability 검사
- grouped interpretation
- 목적이 prediction인지 설명인지 구분

## 10. Probability와 calibration

Logistic regression은 조건이 맞을 때 비교적 calibrated될 수 있지만 자동 보장은 아니다.

- class weight·sampling
- regularization
- distribution shift
- model misspecification
- label noise

Validation에서 reliability diagram과 Brier/log loss를 확인한다. Threshold는 별도로 선택한다.

## 11. Robust·quantile regression

Squared loss가 outlier에 지나치게 민감하면 Huber loss 같은 robust objective를 고려할 수 있다. 특정 quantile을 예측해 비대칭 비용을 표현할 수도 있다.

Objective 선택이 실제 error cost와 일치하는지 검토한다. 여러 loss를 test에 맞춰 고르지 않는다.

## 12. Linear model을 강한 baseline으로 만드는 법

1. Problem·split·metric을 먼저 고정한다.
2. 누출 없는 preprocessing pipeline을 만든다.
3. Dummy와 rule baseline을 기록한다.
4. Regularized linear model을 validation한다.
5. Threshold·calibration을 별도로 검토한다.
6. Coefficient가 아니라 error slice를 먼저 본다.
7. 복잡한 모델이 개선하는 사례와 비용을 비교한다.

## 13. 해석

Coefficient, odds ratio와 feature contribution을 사용할 수 있지만 다음을 구분한다.

- model이 사용하는 association
- input 변화에 대한 local prediction 변화
- 실제 세계의 causal effect

Correlated feature, preprocessing과 interaction이 있으면 한 coefficient를 독립적인 설명으로 사용하기 어렵다. Confidence interval도 model specification과 sampling 가정 안에서의 불확실성이다.

## 14. 대표적인 실패

### Scaling 없이 regularization 비교

Feature 단위 차이를 모델 중요도로 오인한다.

### One-hot trap을 기계적으로 적용

사용하는 모델·regularization·intercept와 무관하게 category 하나를 항상 제거한다. Full-rank 필요와 prediction 목적을 구분한다.

### Accuracy만 보고 logistic model 선택

Probability quality와 threshold cost를 확인하지 않는다.

### Coefficient를 정책 근거로 사용

Association을 intervention 효과로 해석한다.

### 복잡한 모델과 불공정 비교

Linear baseline에는 tuning·preprocessing을 거의 주지 않고 ensemble에는 큰 search budget을 제공한다.

## 15. 리뷰 질문

- Linear relation은 raw feature인가 transformed feature인가?
- Scale과 unit이 coefficient·regularization에 어떤 영향을 주는가?
- Category·missing·unknown을 train pipeline에서 처리하는가?
- Correlated feature에서 coefficient가 안정적인가?
- Probability calibration과 threshold를 분리했는가?
- 복잡한 model이 linear baseline보다 개선하는 오류 사례가 명확한가?
- 해석을 causal claim으로 확대하지 않았는가?

## 실습 연결

누적 실습 4단계의 첫 모델은 regularized logistic regression을 권장한다. `entity_id`, `observation_id`, `event_time` 같은 식별·시간 column을 feature로 직접 넣지 않고, train-only preprocessing과 validation threshold를 기록한다.
