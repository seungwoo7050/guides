# Tree, ensemble과 nearest neighbors

Tree 계열은 비선형 관계와 interaction을 비교적 적은 preprocessing으로 표현하고, nearest neighbors는 “비슷한 입력은 비슷한 결과를 가진다”는 가정을 직접 사용한다. 둘 모두 강력하지만 data geometry와 운영 비용을 이해해야 한다.

## 1. Decision tree

Tree는 feature와 threshold로 입력 공간을 반복 분할한다.

```text
if failures_30d >= 3:
    if activity_7d < 2:
        high risk
```

각 split은 child node의 impurity나 loss 감소를 기준으로 선택한다.

### 장점

- 비선형 관계와 interaction 표현
- numeric scaling이 보통 필수 아님
- 규칙 경로를 관찰 가능
- mixed feature에 유연

### 한계

- 작은 data 변화에 구조가 크게 바뀔 수 있음
- 깊은 tree는 train sample을 외우기 쉬움
- 축에 평행한 step function
- extrapolation에 약함
- leaf probability가 불안정할 수 있음

## 2. Tree regularization

- maximum depth
- minimum samples per split·leaf
- maximum leaves
- impurity decrease threshold
- pruning

Leaf가 작으면 rare pattern을 잡을 수 있지만 variance와 privacy 위험이 커진다. Validation score와 함께 leaf support 분포를 본다.

## 3. Random forest

여러 bootstrap sample과 feature subset에서 tree를 학습해 prediction을 평균·vote한다.

효과:

- 개별 tree variance 감소
- nonlinear interaction 표현
- tabular baseline으로 강함

주의:

- tree 수가 늘면 memory·latency 증가
- probability calibration이 항상 좋지 않음
- rare category·high-cardinality 처리 필요
- out-of-bag score도 selection에 반복 사용하면 과적합 가능

## 4. Gradient boosting

앞선 model의 residual 또는 gradient를 줄이는 weak learner를 순차적으로 추가한다.

주요 hyperparameter:

- number of trees
- learning rate
- depth·leaf count
- subsampling
- regularization
- early stopping

Learning rate와 tree 수는 함께 해석한다. 더 많은 tree가 무조건 더 좋은 것은 아니며 training time과 overfitting을 확인한다.

## 5. Bagging과 boosting의 차이

### Bagging

여러 model을 비교적 독립적으로 학습해 평균한다. Variance 감소가 주 목적이다.

### Boosting

이전 단계의 오류를 보완하도록 순차 학습한다. Bias를 줄일 수 있지만 noise와 잘못된 label을 추적할 수 있다.

둘을 “어떤 library class가 더 좋다”로 비교하지 않는다. Dataset size, noise, latency와 calibration 목적을 본다.

## 6. Feature importance

### Impurity-based importance

Tree split에서 impurity 감소를 누적한다. High-cardinality·연속 feature에 편향될 수 있고 correlated feature 사이에서 importance가 분산·대체될 수 있다.

### Permutation importance

평가 data에서 feature 값을 섞어 성능 하락을 본다.

주의:

- correlated feature를 하나만 섞으면 다른 feature가 정보를 대체할 수 있다.
- distribution 밖의 비현실적인 조합을 만들 수 있다.
- importance는 causal effect가 아니다.
- 평가 metric과 dataset에 의존한다.

## 7. Partial dependence와 local explanation

특정 feature를 바꿨을 때 평균 prediction 변화를 시각화할 수 있다. Feature independence 가정이 깨지면 현실에 없는 조합을 평가할 수 있다.

Local explanation도 모델의 현재 prediction을 근사할 뿐 실제 사건의 원인을 증명하지 않는다. 설명 안정성, baseline 선택과 correlated feature를 검토한다.

## 8. Nearest neighbors

새 입력과 가까운 train sample의 label을 사용한다.

핵심 가정:

```text
선택한 representation과 distance에서 가까운 sample은 비슷한 outcome을 가진다.
```

### Hyperparameter

- `k`
- distance metric
- neighbor weighting
- feature scaling

작은 `k`는 local pattern을 잡지만 noise에 민감하고, 큰 `k`는 smoothing이 커진다.

## 9. Distance의 저주

Dimension이 커지면 모든 sample 사이 거리가 비슷해질 수 있다. 불필요한 feature와 scale이 neighbor 의미를 망친다.

대응:

- domain feature selection
- scaling
- dimensionality reduction
- metric learning 또는 embedding
- approximate nearest neighbor가 필요한 규모인지 분리

## 10. Inference cost

Tree ensemble은 tree 수·depth에 따라, KNN은 train set 크기에 따라 inference 비용이 증가한다.

검토:

- batch와 online latency
- model memory
- CPU cache·vectorization
- neighbor index build·update
- explanation·logging 비용

Offline metric이 조금 높아도 운영 예산을 넘으면 사용할 수 없다.

## 11. Missing·category 처리

Library와 algorithm에 따라 native missing/category 지원이 다르다. 지원한다는 문구만 믿지 않고 다음을 확인한다.

- missing 방향이 학습되는가
- unknown category 처리
- ordinal encoding이 가짜 순서를 만드는가
- target encoding이 fold 안에서 계산되는가
- category cardinality와 rare value

Target encoding은 특히 leakage가 쉽다. Out-of-fold 방식과 smoothing이 필요하다.

## 12. Probability와 threshold

Tree leaf frequency와 ensemble score는 calibrated probability가 아닐 수 있다. Validation에서 calibration을 확인하고, sampling·class weight를 적용했다면 실제 prevalence에서 다시 평가한다.

## 13. Model stability

Seed·sample·time split을 바꾸며 다음을 본다.

- overall metric
- important slice
- feature importance ranking
- tree depth·leaf support
- extreme probability

Prediction은 안정적인데 explanation만 불안정할 수 있다. 제품 목적과 감사 요구에 따라 허용 범위를 정한다.

## 14. 대표적인 실패

### Default boosting 승리

많은 tuning과 feature engineering을 제공한 boosting을 약한 baseline과 비교한다.

### ID memorization

High-cardinality ID, timestamp나 source code를 tree가 잘라 entity를 기억한다.

### Importance = truth

Impurity importance 순위를 업무 원인으로 해석한다.

### KNN without scaling

단위가 큰 feature가 거리를 지배한다.

### Latency 제외

큰 ensemble의 offline score만 보고 운영 비용을 무시한다.

## 15. 리뷰 질문

- Tree depth와 leaf support가 memorization을 허용하지 않는가?
- Bagging·boosting을 선택한 이유가 error pattern과 연결되는가?
- Category·missing·target encoding이 split 경계를 지키는가?
- Importance·explanation이 correlated feature에서 안정적인가?
- KNN의 distance와 representation이 domain 의미를 가지는가?
- Inference latency·memory·update 비용을 비교했는가?
- Probability와 threshold를 독립적으로 검증했는가?

## 실습 연결

누적 실습 4단계에서 linear model과 작은 tree ensemble을 같은 preprocessing·split·metric에서 비교한다. Ensemble이 개선한 row와 악화한 row를 5단계 error analysis에 연결한다.
