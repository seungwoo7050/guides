# Baseline, metric과 decision rule

모델 평가는 숫자 하나를 고르는 일이 아니다. **예측 품질, probability 품질, action 결과와 운영 capacity**를 서로 다른 검사로 연결하는 일이다.

## 1. Baseline의 종류

### Dummy baseline

- 분류: 항상 다수 class, class prevalence에 따른 무작위 예측
- 회귀: 평균·중앙값·최근 값

Dataset과 metric 구현이 상식적인 결과를 내는지 확인한다.

### Rule baseline

도메인에서 이미 사용하는 간단한 규칙이다.

```text
최근 30일 활동이 0이면 high risk
오류 횟수가 5회 이상이면 review
```

복잡한 모델이 설명·운영 비용을 감수할 만큼 개선되는지 비교한다.

### Operational baseline

현재 사람 절차나 기존 모델이다. 실제 교체 판단에는 가장 중요하지만 offline dataset에서 공정하게 재현하기 어려울 수 있다.

Baseline은 한 개로 제한하지 않는다. dummy, rule, current process를 가능한 범위에서 함께 기록한다.

## 2. Confusion matrix

Binary classification에서 action threshold를 적용하면 네 상태가 생긴다.

| 실제 | 예측 positive | 예측 negative |
|---|---|---|
| positive | True Positive | False Negative |
| negative | False Positive | True Negative |

Metric은 이 네 수를 다른 비율로 요약한다.

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
specificity = TN / (TN + FP)
accuracy  = (TP + TN) / total
F1        = 2 * precision * recall / (precision + recall)
```

분모가 0인 상태를 명시적으로 처리한다. 예를 들어 positive 예측을 하나도 하지 않았다면 precision을 임의로 1로 두지 않는다.

## 3. Accuracy가 실패하는 경우

Positive prevalence가 1%인 dataset에서 모두 negative로 예측하면 accuracy는 99%다. 이 값은 모델이 positive를 찾는 능력을 말하지 않는다.

Class imbalance에서는 다음을 함께 본다.

- prevalence
- precision·recall
- false positive rate
- confusion matrix의 절대 개수
- threshold별 workload
- PR curve 또는 ROC curve

ROC-AUC가 높아도 극히 낮은 false positive rate 구간의 품질은 나쁠 수 있다. 실제 action 영역을 별도로 확인한다.

## 4. Ranking, probability, decision을 분리한다

### Ranking

Positive가 negative보다 높은 score를 받는가. ROC-AUC, average precision 같은 metric이 주로 본다.

### Probability estimation

`0.8`이라고 예측한 집합에서 실제 positive 비율이 약 80%인가. Log loss, Brier score와 calibration curve를 본다.

### Decision

어떤 threshold에서 어떤 action을 취할 것인가. Precision, recall, cost, capacity와 안전 조건을 본다.

좋은 ranking 모델이 반드시 calibrated probability를 제공하지 않는다. 같은 ranking에서도 threshold를 다르게 선택할 수 있다.

## 5. Metric은 업무 비용을 근사한다

오류 비용을 단순화하면 threshold의 expected cost를 계산할 수 있다.

```text
cost = FP * cost_fp + FN * cost_fn + review_count * cost_review
```

실제 비용은 집단·시간·action마다 다를 수 있다. 비용을 정확한 화폐로 환산하기 어렵더라도 다음 우선순위는 명시한다.

- 놓치면 안 되는 오류
- 사람이 검토할 수 있는 최대 건수
- 자동 action이 허용되는 최소 확신
- false alarm이 반복될 때 생기는 피로와 신뢰 손실

Metric을 먼저 고르고 업무 이유를 나중에 붙이지 않는다.

## 6. Threshold

Default `0.5`는 모델이 제공하는 convenience일 뿐 실제 의사결정의 자연스러운 기준이 아니다.

Threshold 선택에는 별도 validation data를 사용한다. 같은 data로 모델을 fit하고 threshold까지 최적화하면 과적합될 수 있다.

Threshold report에는 다음을 포함한다.

- 선택한 threshold와 version
- 선택에 사용한 dataset
- 목표 metric 또는 비용 함수
- precision·recall·FPR·workload
- 주요 slice 결과
- threshold 변화에 대한 민감도
- 운영 capacity가 바뀔 때 조정 규칙

Threshold는 model artifact와 분리해 versioning할 수 있다. 다만 어떤 model version의 score에 적용 가능한지 호환성을 기록한다.

## 7. Calibration

Calibrated classifier의 `0.7` score는 유사한 sample 집합에서 positive가 대략 70%라는 의미를 가져야 한다.

검사 방법:

- reliability diagram
- Brier score
- log loss
- expected calibration error 같은 요약값과 bin별 표본 수

주의:

- 작은 bin은 불확실성이 크다.
- 전체 calibration이 좋아도 중요한 subgroup에서 나쁠 수 있다.
- calibration model도 독립된 validation data가 필요하다.
- distribution shift가 생기면 calibration이 빠르게 무너질 수 있다.

## 8. Regression metric

### MAE

오류 절대값의 평균이다. 단위가 target과 같고 outlier에 MSE보다 덜 민감하다.

### MSE와 RMSE

큰 오류를 더 강하게 벌한다. 실제 비용이 제곱 형태라는 뜻은 아니다.

### Relative·percentage error

0 또는 작은 target에서 폭발할 수 있다. 어떤 row를 제외했는지 확인한다.

### Quantile loss

점 예측이 아니라 특정 quantile을 예측할 때 사용한다. underprediction과 overprediction 비용이 비대칭일 때 유용하다.

항상 residual을 target 범위·시간·집단별로 본다. 평균 metric 하나는 체계적인 편향을 숨길 수 있다.

## 9. Multi-class와 ranking

Multi-class에서는 macro, micro, weighted 평균이 서로 다른 질문에 답한다.

- macro: 각 class를 같은 비중으로 본다.
- micro: 전체 decision을 합쳐 빈도가 큰 class 영향이 크다.
- weighted: class support로 가중한다.

검색·추천·ranking에서는 top-k precision, recall, NDCG 같은 위치 기반 metric을 사용할 수 있다. 그러나 exposure, diversity, novelty와 feedback loop는 별도 시스템 문제다.

## 10. Slice evaluation

전체 metric과 함께 다음 slice를 고른다.

- 중요한 사용자·업무 집단
- 데이터가 적은 집단
- 신규·기존 entity
- 시간대·지역·제품 version
- missing pattern
- score 구간
- 오류 비용이 큰 사례

Slice는 test 결과를 본 뒤 성능이 좋은 것만 고르지 않는다. Problem contract에서 중요한 slice를 미리 정의하고, 탐색 과정에서 새로 발견한 slice는 exploratory로 표시한다.

## 11. 불확실성과 표본 수

Metric은 유한 sample의 추정값이다.

- 분자·분모와 raw count를 함께 보고한다.
- bootstrap 또는 반복 split으로 변동 범위를 추정할 수 있다.
- 매우 작은 slice의 단일 비율을 정밀한 사실처럼 표현하지 않는다.
- 여러 model·metric·slice를 반복 비교하면 우연히 좋은 결과를 고를 가능성이 커진다.

신뢰구간 하나가 모든 불확실성을 포함하지 않는다. Dataset shift, label noise와 selection bias는 표본 오차와 다른 문제다.

## 12. Online outcome

Offline metric이 좋으면 online experiment 또는 제한된 rollout의 가설이 생긴다.

```text
모델 score 품질
→ action 정책
→ 사람·시스템 반응
→ 제품 outcome
```

Shadow, canary, A/B test 같은 방식으로 latency, workload, override, 실제 비용과 사용자 결과를 확인할 수 있다. 고위험 action은 domain review와 별도 안전 절차가 필요하다.

## 13. 대표적인 실패

### Metric shopping

여러 metric 중 가장 좋아 보이는 것만 보고하고 선택 과정을 숨긴다.

### AUC-only report

실제 threshold, precision, recall과 workload 없이 ranking metric만 제시한다.

### Threshold on test

Final test에서 최적 threshold를 고르고 같은 test 성능을 최종 결과로 보고한다.

### Relative improvement만 보고

Baseline 0.01에서 0.02로 두 배 향상됐다는 표현은 실제 유용성을 숨길 수 있다. 절대값과 raw count를 함께 제공한다.

### 모델 비교와 의사결정 비교 혼동

Model A와 B의 probability는 같지만 threshold가 다르거나, ranking은 좋아졌지만 action cost는 나빠질 수 있다.

## 14. 리뷰 질문

- Dummy, rule, 현재 운영 baseline이 있는가?
- Metric이 실제 오류 비용과 capacity를 반영하는가?
- Ranking·probability·decision을 분리해 평가했는가?
- Threshold는 train과 독립된 data에서 선택했는가?
- Raw confusion matrix와 분모를 제공하는가?
- 중요한 slice와 작은 sample의 불확실성을 보고하는가?
- Calibration을 필요한 경우 검증했는가?
- Offline 개선이 어떤 online 가설로 이어지는가?

## 실습 연결

[`examples/metrics.py`](../../examples/metrics.py)는 표준 라이브러리만으로 confusion matrix, precision, recall, F1, Brier score와 log loss를 계산한다. 누적 실습 3·5단계에서는 dummy·rule baseline과 threshold report를 같은 split manifest에서 만든다.
