# 누적 실습: Model lifecycle

이 실습은 작은 합성 churn dataset을 사용해 문제 정의부터 model release review까지 누적한다. 학습자 workspace에는 정답 코드를 복사하지 않으며 model library와 구현 세부는 학습자가 선택한다. 대신 결과·실패를 비교할 수 있는 표준 라이브러리 CPU [`reference`](reference/README.md), dataset·split·보고서·artifact 계약과 공개 검사를 제공한다.

## 목적

```text
문제 계약
→ dataset·split audit
→ baseline
→ classical model 비교
→ threshold·slice·calibration 평가
→ 작은 neural model
→ model bundle·inference contract
→ model card·monitoring·release decision
```

높은 score가 완료 조건은 아니다. Test 독립성, leakage 부재, baseline 비교, 실패 분석과 artifact 추적성이 더 중요하다.

## 지원 방식

### 저장소가 제공하는 것

- 재생성 가능한 합성 dataset
- entity-disjoint split manifest
- schema와 prediction 금지 field
- 단계별 산출물 계약
- Markdown·JSON template
- workspace 생성기
- 구조·fixture·mutation 검사기
- 8단계 완성 reference와 결정성·clean-process inference test
- 미완성 starter와 대표적인 알려진 오답

### 학습자가 구현하는 것

- baseline과 model training
- preprocessing pipeline
- metric·threshold·slice 분석
- 선택 시 neural training
- 실제 model serialization과 smoke test
- 해석·limitation·release decision

External ML package 없이도 1~3·5·7·8단계의 문서와 일부 기준 계산을 진행할 수 있다. 4·6단계의 실제 model 구현에는 NumPy, scikit-learn 또는 PyTorch를 선택할 수 있다.

## Fixture

```text
fixtures/
├── dataset.csv
├── schema.json
├── split_manifest.csv
├── split-policy.json
├── dataset-card.md
└── fixture-manifest.json
```

Dataset은 240개 synthetic entity의 3개월 snapshot, 총 720 row다. 같은 entity는 하나의 split에만 속한다.

`future_refund_30d`는 의도적인 leakage hazard다. Outcome 이후에만 알 수 있고 prediction에는 사용할 수 없다.

Fixture 검증:

```sh
python3 ../../scripts/verify-fixtures.py
```

## 작업 공간

```sh
../../scripts/new-workspace.sh
```

또는 저장소 루트에서:

```sh
./scripts/new-workspace.sh
```

다음 경로를 만든다.

```text
exercises/model-lifecycle/workspace/
```

기존 workspace는 덮어쓰지 않는다. `skeleton/`, `fixtures/`와 `templates/`는 직접 수정하지 않는다.

생성 도중 중단돼 `.workspace.lock`만 남았다면 먼저 다른 `new-workspace.sh`가 실행 중이 아닌지 확인한다. `workspace/`가 존재하지 않고 lock 디렉터리가 비어 있을 때만 저장소 루트에서 다음처럼 복구한다.

```sh
rmdir exercises/model-lifecycle/.workspace.lock
./scripts/new-workspace.sh
```

기존 `workspace/`는 stale lock 복구를 위해 이동·삭제하지 않는다. Reference builder와 현대 모델 builder도 지정한 **새 빈 output**만 사용하며 기존 결과가 있으면 실패한다.

## 단계 검사

```sh
python3 ../../scripts/check-submission.py \
  --workspace workspace \
  --stage 1
```

저장소 루트에서는 다음과 같다.

```sh
python3 scripts/check-submission.py \
  --workspace exercises/model-lifecycle/workspace \
  --stage 1
```

`--stage N`은 1단계부터 N단계까지 누적 검사한다.

검사기는 다음만 확인한다.

- 파일 존재
- JSON·JSONL parse
- 필수 heading과 field
- version·digest 형식
- stage 간 일부 참조 일관성

다음은 자동으로 완전히 증명하지 않는다.

- model이 올바르게 학습됐는가
- leakage가 전혀 없는가
- metric·threshold가 업무에 타당한가
- 오류 사례 해석이 정확한가
- model card의 위험 판단이 충분한가

## 공통 규칙

1. `fixtures/split_manifest.csv`를 test 결과에 맞게 바꾸지 않는다.
2. Test는 model·feature·hyperparameter·threshold 선택에 사용하지 않는다.
3. Preprocessing state는 training split에만 fit한다.
4. 모든 report에 dataset·split version 또는 digest를 기록한다.
5. 실행하지 않은 선택 측정은 근거와 함께 `not-run`으로 표시하되 필수 측정을 건너뛴 단계를 완료로 표시하지 않는다.
6. Actual model artifact가 없으면 7단계 중간 manifest에서만 `not-included`를 사용한다. 8단계는 실제 artifact·digest·golden inference가 필수다.
7. Report에는 선택하지 않은 대안과 limitation을 남긴다.
8. 실제 개인·고객 data를 이 workspace에 넣지 않는다.

## 1단계: 문제 계약

### 읽기

- [`문제 framing`](../../docs/01-framing-and-data/01-ml-system-and-problem-framing.md)
- [`Dataset 계약`](../../docs/01-framing-and-data/02-dataset-contracts-and-documentation.md)

### 산출물

```text
reports/problem-contract.md
```

[`templates/problem-statement.md`](templates/problem-statement.md)를 복사해 작성한다.

필수 내용:

- Prediction subject와 observation unit
- Observation time과 label window
- Primary user와 decision
- False positive·negative·abstention 비용
- Intended·prohibited use
- Model 없이 사용할 baseline
- 성공·중단 조건

### 완료 질문

- Model output이 실제로 어떤 action을 바꾸는가?
- Observation time 이후 정보가 필요한 문제는 아닌가?
- Prediction이 없어도 문제를 측정할 수 있는가?

## 2단계: Dataset과 split audit

### 읽기

- [`Dataset 계약`](../../docs/01-framing-and-data/02-dataset-contracts-and-documentation.md)
- [`Split·leakage`](../../docs/01-framing-and-data/03-splits-leakage-and-sampling.md)

### 산출물

```text
reports/dataset-card.md
reports/split-audit.json
```

Dataset card template을 사용하되 fixture card를 그대로 복사하지 않는다. Prediction 관점에서 각 field를 검토한다.

`split-audit.json` 최소 구조:

```json
{
  "dataset_version": "synthetic-churn-v1",
  "split_policy_version": "entity-hash-v1",
  "rows": {"train": 0, "validation": 0, "test": 0},
  "entities": {"train": 0, "validation": 0, "test": 0},
  "positives": {"train": 0, "validation": 0, "test": 0},
  "entity_overlap": [],
  "duplicate_row_ids": [],
  "forbidden_features": ["future_refund_30d"],
  "valid": true,
  "limitations": []
}
```

숫자는 fixture를 직접 읽어 계산한다.

### 완료 질문

- 왜 random row split보다 entity split이 적합한가?
- Time shift를 평가하지 못하는 이유는 무엇인가?
- 어떤 field가 prediction time에 존재하지 않는가?

## 3단계: Baseline과 metric

### 읽기

- [`Baseline·metric·decision rule`](../../docs/01-framing-and-data/04-baselines-metrics-and-decision-rules.md)
- [`Loss와 risk`](../../docs/02-learning-and-generalization/01-loss-risk-and-learning.md)

### 산출물

```text
reports/baseline.json
```

최소 baseline:

- constant·prevalence baseline
- 업무 rule baseline

권장 구조:

```json
{
  "dataset_version": "synthetic-churn-v1",
  "selection_split": "validation",
  "selection_metric": "...",
  "decision_context": {"review_budget_fraction": 0.2},
  "baselines": [
    {"name": "constant", "validation": {}}
  ],
  "chosen_baseline": "...",
  "choice_reason": "...",
  "known_limitations": []
}
```

### 완료 질문

- Accuracy가 어떤 class imbalance를 숨기는가?
- Probability metric과 action metric을 왜 분리하는가?
- Model이 baseline을 못 이기면 어떤 결론이 가능한가?

## 4단계: Classical model 비교

### 읽기

- [`선형 model`](../../docs/03-classical-models/01-linear-models.md)
- [`Tree·ensemble·neighbors`](../../docs/03-classical-models/02-trees-ensembles-and-neighbors.md)
- [`Preprocessing pipeline`](../../docs/03-classical-models/04-preprocessing-pipelines-and-interpretation.md)

### 산출물

```text
reports/classical-experiments.jsonl
src/model_project/
```

최소 두 run을 기록하고 하나는 선형 model로 한다. 각 line은 완전한 JSON object다.

필수 field:

```text
run_id
hypothesis
dataset_version
split_policy_version
feature_schema_version
model
preprocessing
seed
validation
artifact_status
interpretation
```

Test 결과는 이 단계에 넣지 않는다.

### 완료 질문

- 어떤 변환이 fitted state를 갖는가?
- 한 run에서 무엇만 바꿨는가?
- Validation improvement가 seed variation보다 큰가?

## 5단계: Final evaluation

### 읽기

- [`Validation·selection·uncertainty`](../../docs/02-learning-and-generalization/03-validation-model-selection-and-uncertainty.md)
- [`Preprocessing과 해석`](../../docs/03-classical-models/04-preprocessing-pipelines-and-interpretation.md)

### 산출물

```text
reports/evaluation.json
```

필수 내용:

- 선택된 run과 선택 근거
- Validation에서 고정한 threshold
- Test confusion matrix와 metric
- Brier score 또는 calibration table
- plan·region·tenure slice
- 대표 false positive·negative
- claim과 limitation

Test를 본 뒤 model·threshold를 바꿨다면 그 실행은 final test가 아니다. 새로운 holdout 없이 최종 주장을 확대하지 않는다.

## 6단계: 작은 신경망

### 읽기

- [`Tensor·autodiff`](../../docs/04-neural-networks/01-tensors-autodiff-and-computation-graphs.md)
- [`Training loop`](../../docs/04-neural-networks/03-training-loop-and-optimization.md)
- [`학습 실패 디버깅`](../../docs/04-neural-networks/04-debugging-neural-training.md)
- [`Capstone B`](../../docs/07-capstones/02-small-neural-model.md)

### 산출물

```text
reports/neural-experiment.json
```

필수 내용:

- Input·hidden·output shape
- Parameter count
- Loss·optimizer·learning rate
- 작은 batch overfit 결과
- Epoch별 training·validation trace
- Gradient 또는 update 확인
- Checkpoint rule
- 여러 seed 또는 variation
- Classical baseline과 비교
- 최소 세 개의 failure diagnosis

신경망이 classical model보다 좋지 않아도 report는 유효하다.

## 7단계: Model bundle과 inference

### 읽기

- [`실험과 artifact`](../../docs/06-model-lifecycle/01-experiments-reproducibility-and-artifacts.md)
- [`Inference 계약`](../../docs/06-model-lifecycle/02-inference-contracts-and-delivery.md)

### 산출물

```text
artifacts/model-bundle/
├── manifest.json
├── input-schema.json
├── preprocessing.json
├── decision-policy.json
├── evaluation.json
└── model-card.md
reports/inference-contract.md
```

7단계에서는 contract review를 먼저 끝내기 위해 실제 model artifact를 보류할 수 있다.

- 포함하면 checksum과 clean-process smoke test를 추가한다.
- 아직 포함하지 않으면 manifest에 `model_artifact_status: not-included`를 기록하고 필요한 format·loader·test를 설명한다.
- `not-included`는 7단계 중간 상태일 뿐 최종 완료가 아니다.

### 완료 질문

- Feature order와 fitted state는 어디 있는가?
- Output probability와 action policy version을 분리했는가?
- Invalid input, unknown category와 timeout은 어떤 결과인가?
- 이전 bundle로 rollback할 수 있는가?

## 8단계: Model card, monitoring과 release decision

### 읽기

- [`Monitoring·retraining`](../../docs/06-model-lifecycle/03-monitoring-drift-and-retraining.md)
- [`위험·model card`](../../docs/06-model-lifecycle/04-risk-documentation-and-model-cards.md)
- [`Model release review`](../../docs/07-capstones/03-model-release-review.md)

### 산출물

```text
reports/model-card.md
reports/monitoring-plan.md
reports/release-decision.md
reports/reproduction.json
artifacts/model-bundle/model.json
artifacts/model-bundle/checksums.json
artifacts/model-bundle/golden-inputs.jsonl
artifacts/model-bundle/golden-predictions.jsonl
artifacts/model-bundle/reproduction.json
```

8단계에서는 `model_artifact_status: included`인 실제 artifact가 필수다. Manifest의
SHA-256과 전체 checksum 목록을 확인하고, 새 process에서 golden input을 읽어
golden prediction과 parity를 검사한다. Reproduction evidence에는 fixture digest,
runtime 요구사항, 실행 명령, seed와 비-network 조건을 기록한다. Artifact를
직렬화할 수 없거나 smoke test가 실패하면 이 단계는 완료가 아니다.

Decision은 다음 중 하나다.

```text
APPROVE
APPROVE WITH CONDITIONS
DEFER
REJECT
```

합성 dataset에서 점수가 좋아도 실제 사용자 대상 release를 승인할 수는 없다. 이 실습의 승인은 **합성 환경에서 다음 개발 단계로 이동 가능한가**를 뜻한다.

## 최종 review

다음 명령은 구조만 검사한다.

```sh
python3 ../../scripts/check-submission.py --workspace workspace --stage 8
```

그 뒤 [`시스템 종합 검토`](../../docs/90-system-review.md)의 질문으로 동료 review를 수행한다.

공개 reference와 negative control을 재생하려면 저장소 루트에서 다음을 실행한다.

```sh
python3 exercises/model-lifecycle/tests/check.py --candidate exercises/model-lifecycle/reference
python3 exercises/model-lifecycle/tests/check.py --candidate exercises/model-lifecycle/skeleton
for candidate in exercises/model-lifecycle/known_bad/*/; do
  python3 exercises/model-lifecycle/tests/check.py --candidate "$candidate"
done
```

첫 명령만 성공해야 한다. 필수 검증은 작은 합성 fixture와 CPU에서 제한된 시간 안에 실행되며 네트워크·GPU·유료 자원을 사용하지 않는다.

최종 결과에 다음을 함께 남긴다.

- 실행 명령과 environment
- source revision
- dataset·split digest
- 실패한 실험과 선택하지 않은 대안
- 자동 검사로 증명하지 못한 주장
- 실제 dataset으로 이동할 때 필요한 추가 검토
