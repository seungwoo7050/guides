# Preprocessing pipeline과 해석

실무에서 모델은 estimator 하나가 아니라 **입력 schema부터 변환·prediction·threshold까지 이어지는 pipeline**이다. 평가와 배포가 같은 pipeline을 사용하지 않으면 모델 파일이 같아도 다른 시스템이다.

## 1. Fit과 transform

Preprocessor는 보통 두 단계가 있다.

```text
fit(train)       train에서 통계·vocabulary·mapping 학습
transform(data)  고정된 상태로 data 변환
```

Validation/test에서 다시 fit하지 않는다. 다음은 모두 learned state다.

- 평균·분산
- imputation value
- category vocabulary
- feature selection
- PCA component
- target encoding statistic
- text vocabulary·IDF

Pipeline은 estimator와 함께 이 상태를 묶는다.

## 2. Column contract

각 입력 column에 다음을 기록한다.

- 이름과 semantic
- type과 unit
- nullability
- 허용 범위·category
- 예측 시 availability
- preprocessing
- unknown 처리
- feature name after transform

Column 순서에 의존하는 raw array보다 named schema를 경계에서 검증한다.

## 3. Numeric preprocessing

### Scaling

Standardization, min-max, robust scaling은 모델과 outlier 특성에 따라 선택한다. Tree에는 필수가 아닐 수 있지만 linear·distance·gradient model에는 중요하다.

### Imputation

평균·중앙값·constant·model-based 방법을 사용할 수 있다. Missing mechanism과 운영 의미를 기록한다. Train에서 fit하고 missing indicator 필요성을 검토한다.

### Transformation

Log, clipping, binning과 nonlinear basis는 outlier와 관계 shape를 바꾼다. Threshold를 사후 data snooping으로 정하지 않는다.

## 4. Category preprocessing

### One-hot

명시적인 category별 indicator를 만든다. High cardinality에서 feature 수가 커진다.

### Ordinal encoding

실제 순서가 있을 때만 사용한다. 임의 정수 mapping은 distance·linear model에 가짜 순서를 준다.

### Target encoding

Category별 label 통계를 사용한다. Leakage 위험이 크므로 out-of-fold 계산, smoothing, unknown 처리와 train-only fit이 필요하다.

### Unknown과 rare category

운영에서 새 category가 나타날 수 있다. 오류, unknown bucket, hashing 중 정책을 명시한다. Rare category grouping은 group 의미와 공정성 영향을 검토한다.

## 5. Text preprocessing

- Unicode normalization
- tokenization
- vocabulary
- n-gram
- count·TF-IDF
- truncation·padding

Train corpus로 vocabulary와 IDF를 fit한다. Document source, duplicate와 near-duplicate가 split을 넘지 않는지 확인한다.

## 6. Date와 time

Timestamp를 raw 정수로 넣기 전에 의미를 분리한다.

- age since event
- hour·day·season
- recency
- duration
- cutoff 이전 window aggregate

Timezone, daylight saving, late event와 미래 정보 누출을 검토한다. Absolute timestamp는 특정 기간·정책을 memorization하는 shortcut이 될 수 있다.

## 7. Identifier

`user_id`, `transaction_id`, row number는 보통 feature가 아니다. 직접 제거해도 다음 proxy가 남을 수 있다.

- 거의 유일한 timestamp
- source-specific code
- free-text signature
- rare category combination

Entity memorization을 group split과 ablation으로 확인한다.

## 8. End-to-end pipeline

Pipeline이 포함해야 하는 범위:

```text
schema validation
→ column selection
→ preprocessing
→ model score
→ calibration(optional)
→ threshold 또는 decision policy
→ output schema
```

Threshold를 model 밖에 둘 수 있지만 release compatibility를 기록한다. Prediction 후 사람이 임의로 후처리하는 규칙도 versioned system 일부다.

## 9. Pipeline 평가

Cross-validation과 hyperparameter search는 pipeline 전체를 fit한다. Preprocessed matrix를 미리 전체 dataset으로 만들어 두고 estimator만 CV하면 leakage가 생길 수 있다.

검사:

- split별 preprocessor state가 다르게 fit되는가
- test row가 vocabulary·imputer에 들어가지 않는가
- feature order와 names가 보존되는가
- serialize·load 뒤 같은 prediction인가
- batch size 1과 여러 row가 같은 의미인가

## 10. Interpretation의 대상

먼저 무엇을 설명하려는지 정한다.

- model 전체의 평균 behavior
- 특정 prediction
- feature 변화에 대한 sensitivity
- 오류 사례
- 실제 세계의 원인

앞의 네 가지는 모델 분석으로 일부 접근할 수 있지만 마지막 인과 설명은 별도 근거가 필요하다.

## 11. Global interpretation

- linear coefficient
- tree feature importance
- permutation importance
- partial dependence
- aggregate error slice

각 방법은 model, dataset와 metric에 의존한다. Correlated feature와 비현실적인 feature 조합을 확인한다.

## 12. Local interpretation

한 prediction에 feature contribution 또는 local surrogate를 제공할 수 있다.

검토:

- baseline/reference input 선택
- 근사 fidelity
- seed·parameter 안정성
- correlated feature 분배
- 사용자가 원인으로 오해할 가능성
- explanation latency와 version

Local explanation이 model prediction을 정당화하거나 올바르게 만든다는 뜻은 아니다.

## 13. Error analysis가 먼저다

Feature importance보다 다음 질문이 더 직접적이다.

- 어떤 row에서 크게 틀리는가
- label이 모호하거나 잘못됐는가
- missing·unknown이 있는가
- 특정 source·time·group인가
- threshold 근처인가
- baseline도 같은 오류를 내는가

Model을 설명하기 전에 data와 evaluation failure를 조사한다.

## 14. Pipeline artifact

Model release에는 최소한 다음이 필요하다.

```text
input schema version
preprocessing state
feature order·names
model parameter
calibration state
threshold policy 또는 compatibility ID
library·runtime version
training data·split reference
evaluation report
```

Pickle류 artifact는 untrusted source에서 load하면 코드 실행 위험이 있을 수 있다. Serialization format과 신뢰 경계를 문서화한다.

## 15. Train-serving skew

Training과 inference가 feature를 다르게 계산한다.

예:

- SQL과 online service의 집계 window 차이
- timezone·rounding 차이
- category mapping version 차이
- missing default 차이
- batch와 online code path 차이

대응:

- shared transformation code 또는 spec
- golden input-output fixture
- shadow comparison
- feature value logging과 digest
- schema compatibility test

## 16. 대표적인 실패

### Notebook-only preprocessing

수동 cell 순서와 전역 상태에 의존해 release에서 재현되지 않는다.

### Precompute before split

전체 dataset에 imputation·scaling·PCA를 fit한다.

### Feature names lost

Array column 순서가 바뀌어도 shape가 같아 prediction이 조용히 잘못된다.

### Explanation as approval

그럴듯한 local explanation을 model correctness의 증거로 사용한다.

### Unsafe artifact load

외부에서 받은 pickle을 신뢰 경계 없이 load한다.

## 17. 리뷰 질문

- 모든 learned preprocessing state가 train에서만 fit되는가?
- Input schema·unit·unknown·missing 정책이 명시됐는가?
- Feature name과 order가 artifact에 보존되는가?
- Cross-validation이 pipeline 전체를 다시 fit하는가?
- Training과 serving transformation을 golden fixture로 비교하는가?
- Interpretation 방법의 가정과 instability를 기록하는가?
- 오류 분석이 explanation보다 먼저 수행됐는가?
- Artifact format의 보안·호환 경계를 알고 있는가?

## 실습 연결

누적 실습 4단계에서는 preprocessing과 estimator를 하나의 pipeline으로 저장하고, validation/test에 `fit`이 호출되지 않음을 검사하는 테스트를 작성한다. 7단계 artifact bundle에는 input schema와 golden prediction fixture를 포함한다.
