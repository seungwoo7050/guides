# Validation, model selection과 uncertainty

Validation은 모델이 좋은지 한 번 측정하는 절차가 아니다. **여러 후보 가운데 하나를 선택하는 과정 전체를 평가 data와 분리하고, 선택 결과의 불확실성을 제한하는 절차**다.

## 1. Model selection은 넓다

다음 선택은 모두 validation에 적응한다.

- feature 포함·제외
- preprocessing 방식
- model family
- hyperparameter
- random seed 중 가장 좋은 run
- checkpoint와 early stopping
- threshold와 calibration
- slice·metric 선택
- 데이터 제외 규칙

코드의 `fit`에 들어가지 않았다고 selection이 아닌 것은 아니다.

## 2. Holdout validation

Dataset이 충분하면 train·validation·test를 고정한다.

장점:

- 단순하고 실행 비용이 낮다.
- 반복 실험 비교가 쉽다.

한계:

- 작은 dataset에서는 split 우연성에 민감하다.
- validation을 많이 볼수록 과적합한다.
- 특정 기간·group 구성에 결과가 의존한다.

Split manifest와 사용 이력을 기록한다.

## 3. Cross-validation

여러 fold에서 train·evaluation을 반복한다.

```text
fold 1 score
fold 2 score
...
mean, standard deviation, worst fold
```

주의:

- preprocessing은 fold train에서 fit한다.
- group·time 구조에 맞는 splitter를 사용한다.
- fold score가 독립이라는 단순 가정을 주의한다.
- hyperparameter search를 같은 CV로 수행하면 보고 score가 selection bias를 포함할 수 있다.

## 4. Nested cross-validation

바깥 fold는 최종 평가, 안쪽 fold는 hyperparameter 선택에 사용한다.

```text
outer train
  └─ inner CV로 후보 선택
outer test
  └─ 선택된 pipeline 평가
```

작은 dataset에서 model selection까지 포함한 성능을 추정할 때 유용하지만 계산 비용이 크다. 모든 프로젝트에 의무는 아니다. 중요한 것은 selection과 final claim의 경계를 이해하는 것이다.

## 5. Hyperparameter search

### Grid search

작은 이산 공간을 모두 탐색한다. Dimension이 늘면 조합 수가 빠르게 커진다.

### Random search

분포에서 조합을 sample한다. 일부 hyperparameter만 중요할 때 효율적일 수 있다.

### Sequential·Bayesian search

이전 결과를 사용해 다음 후보를 고른다. Search algorithm 자체가 validation 결과에 적응한다.

Search report에는 다음을 남긴다.

- 탐색 공간과 prior/range
- trial 수와 budget
- early termination 규칙
- 실패한 run 포함 여부
- selection metric
- 동일 compute 비교 여부
- best와 near-best 후보의 차이

무한히 넓은 범위를 탐색하고 좋은 결과만 남기지 않는다.

## 6. Fair model comparison

후보를 같은 조건에서 비교한다.

- 같은 train·validation split
- 같은 input feature availability
- 같은 evaluation code
- 비슷한 compute 또는 compute를 명시
- 같은 threshold policy 또는 score 자체 비교
- preprocessing 포함한 end-to-end pipeline

Model A는 raw feature, Model B는 future-derived feature를 사용하면서 architecture 성능으로 비교하면 안 된다.

## 7. Randomness

Random seed는 다음에 영향을 준다.

- split
- initialization
- batch order
- augmentation
- dropout
- parallel kernel

Seed 하나를 고정하면 한 run을 반복하기 쉬워지지만 결과의 변동성을 알려주지 않는다. 중요한 비교는 여러 seed 또는 여러 split에서 반복하고 평균·분산·최저값을 본다.

“좋은 seed”를 고르는 것도 hyperparameter selection이다.

## 8. Uncertainty의 종류

### Sampling uncertainty

유한 evaluation sample 때문에 metric이 변한다.

### Model uncertainty

학습 data가 부족한 영역에서 parameter나 prediction이 불확실하다.

### Aleatoric uncertainty

관측 noise나 본질적 randomness처럼 data 자체에 남는 불확실성이다.

### Distribution uncertainty

배포 입력이 학습·평가 분포와 다를 수 있다.

하나의 confidence score가 이 모든 불확실성을 나타내지 않는다.

## 9. Confidence interval과 bootstrap

Evaluation row를 재표본화해 metric 분포를 근사할 수 있다.

주의:

- row가 독립이 아니면 entity/group 단위 bootstrap이 필요하다.
- time series는 block 구조를 고려한다.
- 작은 class와 rare slice에서는 interval이 매우 넓을 수 있다.
- bootstrap은 dataset selection bias와 distribution shift를 해결하지 않는다.

Point estimate와 raw count, interval을 함께 제공한다.

## 10. Statistical significance와 practical significance

작은 차이가 통계적으로 감지돼도 실제 가치가 없을 수 있다. 반대로 중요한 개선이 sample 부족으로 불확실할 수 있다.

검토 항목:

- 절대 metric 차이
- 오류 건수 변화
- action cost와 workload 변화
- latency·memory·운영 복잡도
- 중요한 slice의 변화
- interval과 반복 안정성

P-value 하나로 model 선택을 자동화하지 않는다.

## 11. Multiple comparisons

많은 model·feature·metric·slice를 탐색하면 우연히 좋은 결과를 발견한다.

대응:

- 사전 지정한 primary metric
- trial 전체 기록
- validation 사용 횟수 추적
- independent final test
- holdout refresh
- 탐색 결과와 confirmatory 결과 구분

Leaderboard를 반복 확인하는 것도 multiple comparison이다.

## 12. Calibration과 threshold selection

Model selection, calibration과 threshold tuning은 서로 다른 단계일 수 있다.

```text
train: model parameter 학습
validation A 또는 CV: model/hyperparameter 선택
validation B 또는 out-of-fold prediction: calibration·threshold
final test: 고정된 pipeline과 decision 평가
```

Data가 작으면 절차를 단순화할 수 있지만 어떤 단계가 같은 data를 공유했는지 명시하고 주장 강도를 낮춘다.

## 13. Error analysis

Validation error를 model 개선에 사용한다.

- false positive·false negative 예시
- score가 가장 틀린 사례
- missing pattern
- group·time·source slice
- label ambiguity
- preprocessing failure
- shortcut evidence

Error analysis에서 feature나 rule을 바꾸면 같은 validation에 적응한다. 변경을 반복한 뒤 final test 또는 새 시간 구간으로 확인한다.

## 14. Test result 해석

Final test는 다음 질문에 답한다.

```text
고정된 problem·data·pipeline·threshold가
이 test가 대표하는 환경에서
어느 정도 성능을 보였는가?
```

답하지 못하는 것:

- 모든 미래 환경의 품질
- 인과 효과
- 안전성 전체
- 작은 slice의 정밀한 성능
- 운영 장애와 latency

Test 결과를 범위 있는 주장으로 기록한다.

## 15. 대표적인 실패

### Best run reporting

여러 seed 중 최고만 보고한다.

### Search budget 불공정

한 모델은 대규모 tuning, 다른 모델은 default로 비교한다.

### Validation set exhaustion

오랜 기간 같은 validation을 조직 전체가 사용해 benchmark에 적응한다.

### Interval 없는 작은 차이

0.001 향상을 결정적인 개선으로 표현한다.

### Test after every commit

Test가 사실상 development dashboard가 된다.

## 16. 리뷰 질문

- 어떤 선택이 validation 결과의 영향을 받았는가?
- Split 구조가 실제 generalization target을 모사하는가?
- Search space와 trial budget을 모두 기록했는가?
- Seed·fold 변동과 worst case를 봤는가?
- 비교가 feature·compute·threshold에서 공정한가?
- Error analysis 뒤 변경을 어디에서 확인했는가?
- Final test를 몇 번 사용했는가?
- Point estimate 외에 raw count와 불확실성을 제공하는가?

## 실습 연결

누적 실습 4단계의 `classical-experiments.jsonl`은 모든 trial을 append-only로 기록한다. 5단계에서는 validation에서 threshold와 calibration을 고정한 뒤 test 결과를 한 번의 release candidate 평가로 남긴다.
