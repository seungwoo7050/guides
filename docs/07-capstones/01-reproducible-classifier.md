# Capstone A: 재현 가능한 분류기

이 capstone은 머신러닝 입문에서 가장 중요한 계약을 하나의 작은 분류 문제로 연결한다. 목표는 높은 점수를 얻는 것이 아니라 **문제·dataset·split·baseline·model·threshold·artifact·report 사이의 추적 가능한 관계**를 만드는 것이다.

누적 실습 [`model-lifecycle`](../../exercises/model-lifecycle/README.md)의 1~5단계와 7~8단계를 완성하면 이 capstone의 기본 요구를 충족할 수 있다.

## 1. 문제

합성 구독 서비스의 월별 snapshot에서 고객이 다음 30일 안에 자발적으로 해지할 가능성을 예측한다.

```text
관측 단위       customer-month snapshot
관측 시점       snapshot_month 말
label           이후 30일 안의 voluntary churn
prediction      churn probability
지원 action     retention 담당자의 수동 검토 우선순위
금지 action     자동 계정 제한·가격 차별·계약 해지
```

Dataset은 학습용 합성 자료다. 실제 제품에서 사용할 수 있다는 근거가 아니다.

## 2. 핵심 학습 질문

- 같은 고객의 여러 snapshot을 어떻게 split할 것인가?
- outcome 이후에만 알 수 있는 field를 어떻게 제외할 것인가?
- majority baseline과 업무 rule baseline 중 무엇이 더 강한가?
- class imbalance에서 accuracy가 어떤 판단을 숨기는가?
- probability와 action threshold를 어떻게 분리할 것인가?
- 전체 metric과 slice 결과가 충돌하면 무엇을 선택할 것인가?
- artifact를 다른 환경에서 재사용하려면 무엇을 함께 전달해야 하는가?

## 3. 제약

### 필수

- 제공된 `dataset.csv`, `schema.json`, `split_manifest.csv`를 사용한다.
- row split을 임의로 다시 만들지 않는다.
- test 결과를 보며 model·feature·threshold를 선택하지 않는다.
- 최소 두 baseline을 구현한다.
- 최소 두 model candidate를 같은 validation 계약에서 비교한다.
- preprocessing state를 training split에서만 fit한다.
- final test는 선택을 고정한 뒤 평가한다.
- 전체·slice·calibration 또는 Brier 결과를 보고한다.
- model bundle과 model card를 작성한다.

### 선택

- scikit-learn 또는 직접 구현
- 실제 binary model artifact 또는 구조만 갖춘 illustrative bundle
- plot·notebook
- probability calibration 방법

### 금지

- `future_refund_30d`처럼 schema에서 `allowed_for_prediction: false`인 field 사용
- entity가 train과 validation/test에 동시에 등장하는 split
- test score로 threshold 선택
- test row를 preprocessing `fit`에 사용
- model score만 보고 baseline·slice·오류 사례 생략

## 4. 단계별 작업

### 단계 1. 문제 계약

[`problem-statement.md`](../../exercises/model-lifecycle/templates/problem-statement.md)를 사용해 다음을 고정한다.

- 사용자와 prediction subject
- observation time과 label window
- prediction이 바꾸는 action
- false positive·negative 비용
- 사용하지 않을 action
- 성공을 판단할 metric과 최소 조건

Model 이름과 feature를 먼저 정하지 않는다.

### 단계 2. dataset과 split audit

다음 결과를 만든다.

```text
reports/dataset-card.md
reports/split-audit.json
```

Audit에는 최소한 다음이 있어야 한다.

- row·entity 수
- split별 row·entity·positive 수
- entity overlap 여부
- duplicate row ID
- schema에 없는 column
- prediction 금지 field
- missing·unknown·범위 이상
- group split이 실제 deployment를 모사하는 이유와 한계

### 단계 3. baseline

최소 두 개를 비교한다.

1. 상수 또는 prevalence baseline
2. 단순 업무 rule baseline

예:

```text
support_tickets_90d >= 3 또는 late_payments_180d >= 2이면 positive
```

Rule은 dataset을 보고 무한히 조정하지 않는다. Validation에서 선택하고 test에서는 고정한다.

Report:

```json
{
  "selection_metric": "recall_at_review_budget",
  "review_budget_fraction": 0.2,
  "baselines": [],
  "chosen_baseline": "...",
  "known_limitations": []
}
```

### 단계 4. 고전적 model 비교

최소 한 개는 선형 model을 포함한다.

권장 후보:

- logistic regression
- shallow decision tree
- random forest 또는 gradient boosting
- k-nearest neighbors는 scaling과 비용을 설명할 수 있을 때 선택

비교 시 고정:

- dataset·split
- feature schema
- preprocessing fit boundary
- metric 코드
- threshold selection 규칙

실험마다 하나의 주요 가설을 기록한다.

```json
{"run_id":"...","hypothesis":"...","feature_schema":"...","model":"...","validation":{},"artifact":"...","interpretation":"..."}
```

### 단계 5. 평가와 decision policy

선택한 model에 대해 다음을 수행한다.

- validation에서 threshold 선택
- test에서 threshold 고정
- confusion matrix
- precision·recall·F1 또는 업무 metric
- Brier score 또는 calibration table
- plan tier·region·tenure slice
- false positive·negative 사례 조사
- threshold 변화에 따른 action volume

`best threshold` 하나만 제시하지 않는다. 비용과 capacity가 바뀌면 정책도 바뀐다는 점을 기록한다.

### 단계 6. artifact와 inference 계약

실제 model을 저장할 수 있다면 저장한다. 저장하지 않아도 다음 구조는 완성한다.

```text
artifacts/model-bundle/
├── manifest.json
├── input-schema.json
├── preprocessing.json
├── decision-policy.json
├── evaluation.json
└── model-card.md
```

실제 binary가 없다면 manifest의 `model_artifact_status`를 `not-included`로 두고 구현해야 할 loader·format·smoke test를 설명한다. 존재하지 않는 artifact digest를 꾸며내지 않는다.

### 단계 7. monitoring과 model card

다음 상태를 구분한다.

- schema reject
- feature missing·unknown
- prediction 분포
- review action volume
- mature label cohort 품질
- calibration
- slice regression

Alert마다 owner와 action을 쓴다. Model card에는 intended use, 금지 use, data·평가 근거, limitation, rollback 조건을 포함한다.

## 5. 완료 기준

### 자동으로 확인 가능한 것

- 제출 파일 구조
- JSON parse와 필수 field
- fixture·split manifest 무결성
- artifact manifest와 schema version
- 문서의 필수 heading

### 리뷰로 확인할 것

- prediction contract가 실제 action과 연결되는가?
- split이 deployment 상황을 모사하는가?
- leakage를 체계적으로 조사했는가?
- baseline이 충분히 강한가?
- metric과 threshold가 비용·capacity를 반영하는가?
- final test를 selection에 재사용하지 않았는가?
- slice 결과와 limitation을 숨기지 않았는가?
- artifact와 monitoring 계획이 같은 version을 가리키는가?

## 6. 대표 오답

### test가 가장 높은 model을 선택한다

Test가 validation으로 변한다. 실험을 처음부터 다시 설계하거나 별도 untouched holdout이 필요하다.

### random row split을 사용한다

같은 고객 snapshot이 여러 split에 들어가 entity 특성을 외운 model이 좋아 보일 수 있다.

### scaling을 전체 dataset에서 fit한다

Validation·test 통계가 training preprocessing에 들어간다.

### accuracy 90%만 보고한다

Positive prevalence가 낮으면 상수 model도 높은 accuracy를 만들 수 있다.

### threshold를 0.5로 고정한다

0.5가 업무 비용과 review capacity를 반영한다는 근거가 없다.

### 실제 artifact 없이 “배포 가능”이라고 쓴다

최소한 format·schema·preprocessing·load test·version·rollback 계약이 필요하다.

## 7. 추가 확장

기본 capstone 뒤 선택할 수 있다.

- time-based holdout과 group split 비교
- missingness mechanism별 평가
- calibration method 비교
- uncertainty·abstention policy
- cost-sensitive learning과 threshold policy 비교
- 실제 소규모 공개 dataset으로 계약 이전
- batch inference manifest와 replay

확장 시 원래 test를 계속 보며 model을 고르지 않는다. 새 연구 질문과 평가 집합을 설계한다.
