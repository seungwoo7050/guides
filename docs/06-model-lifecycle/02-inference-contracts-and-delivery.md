# Inference 계약과 전달 경계

학습이 끝났다고 모델 개발이 끝난 것은 아니다. 모델은 새로운 입력을 받아 예측을 반환할 때 비로소 다른 시스템의 의존성이 된다. 이때 필요한 것은 “모델을 호출한다”는 설명이 아니라 **어떤 입력을 어떤 시점에 받아 어떤 의미의 출력을 반환하며, 실패하면 어떤 상태를 남기는지**에 대한 계약이다.

```text
request 또는 batch
→ schema validation
→ feature construction·preprocessing
→ model execution
→ output postprocessing
→ calibration·decision policy
→ response 또는 artifact
```

각 단계는 version과 실패 조건을 가진다.

## 1. inference unit

먼저 한 번의 예측이 무엇을 나타내는지 고정한다.

- 한 사용자, 한 거래, 한 문서, 한 이미지인가?
- 어떤 observation time을 기준으로 하는가?
- 여러 row를 묶는 batch인가?
- 과거 상태를 포함하는 sequence인가?
- 동일 entity의 중복 요청은 허용되는가?

training row와 inference unit이 다르면 offline 평가가 실제 요청을 모사하지 못한다.

예:

```text
training row: 사용자-월 snapshot
online request: 사용자의 현재 event 한 건
```

이 둘 사이에는 집계 window와 feature store 또는 query가 필요하다. 단순히 column 이름이 같다는 이유로 동일 입력이라고 판단하지 않는다.

## 2. input schema

입력 계약에는 타입만이 아니라 의미와 허용 범위를 포함한다.

```json
{
  "schema_version": "churn-input-v1",
  "fields": [
    {
      "name": "tenure_months",
      "type": "integer",
      "required": true,
      "minimum": 0,
      "available_at": "request_time"
    },
    {
      "name": "plan_tier",
      "type": "string",
      "allowed": ["basic", "standard", "premium"],
      "unknown_policy": "map-to-unknown"
    }
  ]
}
```

검토할 항목:

- 필수·선택 field
- scalar·list·tensor shape
- 단위와 timezone
- categorical vocabulary와 unknown 처리
- missing·NaN·infinite value
- 최대 길이와 크기
- observation cutoff
- 개인정보·민감 field
- schema version과 호환성

### silent coercion을 줄인다

문자열 `"17"`을 정수로 자동 변환하거나 알 수 없는 category를 임의 코드로 바꾸면 데이터 오류가 숨는다. 허용할 coercion과 거부할 입력을 명시한다.

### field 순서를 계약으로 착각하지 않는다

CSV나 tensor처럼 순서가 의미를 갖는 형식은 feature order를 artifact에 고정한다. JSON object처럼 이름 기반 형식이라도 preprocessing이 내부 순서를 안정적으로 만들도록 테스트한다.

## 3. preprocessing의 동일성

가장 흔한 전달 실패 중 하나는 training과 inference가 서로 다른 변환을 사용하는 것이다.

```text
training
raw data → fit scaler/vocabulary → transform → model

inference
new data → 저장된 scaler/vocabulary로 transform → model
```

inference에서 새 평균·표준편차나 vocabulary를 `fit`하지 않는다. 다음 상태는 model과 함께 version한다.

- numeric scaling parameter
- imputation value
- category vocabulary와 unknown token
- text tokenizer·normalization
- image resize·channel order
- feature selection과 order
- label map

preprocessing이 code라면 code revision과 config를, data-derived state라면 실제 fitted state를 bundle에 넣는다.

## 4. offline-online skew

같은 feature 이름이라도 생성 시점과 source가 다르면 값이 달라질 수 있다.

원인:

- training query와 online service가 다른 business rule을 사용한다.
- timezone·window boundary가 다르다.
- null과 unknown 처리가 다르다.
- 늦게 도착한 event가 offline에는 포함되지만 online에는 없었다.
- 실수로 outcome 이후 field가 offline feature에 들어갔다.

검증:

1. 과거 실제 request 시점의 feature를 재구성한다.
2. offline pipeline과 serving pipeline 출력을 같은 row ID로 비교한다.
3. field별 허용 오차와 mismatch rate를 측정한다.
4. source·window·version 차이를 기록한다.

가능하면 같은 변환 library 또는 declarative feature definition을 공유한다. 그러나 code 공유만으로 source timing이 같아지는 것은 아니다.

## 5. output schema와 의미

출력 `0.83`은 의미가 없다. 다음을 고정한다.

- score, probability, logit, embedding 중 무엇인가?
- class order는 무엇인가?
- probability가 calibration됐는가?
- uncertainty 또는 abstention이 있는가?
- model version과 decision policy version은 무엇인가?
- 설명 값이 있다면 어떤 기준과 한계를 갖는가?

예:

```json
{
  "model_version": "churn-model-7",
  "schema_version": "churn-output-v2",
  "entity_id": "customer-1042",
  "prediction_time": "2026-08-09T00:00:00Z",
  "churn_probability_30d": 0.83,
  "decision_policy": "retention-offer-v4",
  "action": "manual-review"
}
```

### model output과 action을 분리한다

모델은 확률 또는 score를 반환하고, 별도 decision policy가 threshold·예산·규칙을 적용하는 구조가 변경과 감사에 유리하다.

```text
model version 변경 없이 threshold 조정 가능
threshold 변경 없이 model 비교 가능
정책과 모델의 책임을 별도 검토 가능
```

정책이 모델 artifact 안에 포함될 수도 있지만 version은 구분한다.

## 6. batch와 online inference

### online

- 낮은 latency
- 요청별 validation과 오류
- timeout·cancellation
- 작은 batch 또는 dynamic batching
- dependency 장애와 fallback

### batch

- 큰 dataset snapshot
- partition·resume·idempotency
- row-level 오류와 전체 job 상태
- output manifest와 completeness
- 재실행 시 중복 방지

같은 모델을 사용해도 완료 계약이 다르다.

Batch output에는 최소한 다음을 남긴다.

- 입력 dataset version
- model·schema·policy version
- 처리한 row 수
- 성공·거부·오류 수
- 누락 partition
- output digest와 위치

## 7. 오류 모델

모델 service는 예측 실패를 하나의 `500`으로 뭉치지 않는다.

| 실패 | 예시 | 권장 처리 |
|---|---|---|
| 입력 거부 | 필수 field 없음, 범위 초과 | 호출자 수정 가능한 오류 |
| schema 불일치 | 새 category, tensor shape | version·compatibility 오류 |
| feature unavailable | upstream timeout | 재시도·fallback 여부 명시 |
| model load 실패 | artifact 손상 | traffic 차단·이전 version 유지 |
| inference timeout | resource 부족 | deadline·batch 축소·fallback |
| invalid output | NaN, class mismatch | 결과 폐기·경보 |
| 정책 거부 | confidence 부족 | abstain·manual review |

### 실패 시 상태

- 요청을 재시도해도 안전한가?
- 같은 request ID가 중복 action을 만들 수 있는가?
- partial batch output을 어떻게 표시하는가?
- fallback 결과가 model 결과와 구분되는가?
- 오류 입력을 개인정보 없이 조사할 수 있는가?

외부 action까지 수행하는 책임은 에이전트 또는 애플리케이션 브랜치가 소유한다. 이 문서는 model inference 결과를 안전하게 전달하는 경계까지만 다룬다.

## 8. compatibility와 versioning

### 독립 version

다음 version을 하나로 뭉치지 않는다.

- input schema
- preprocessing
- model weights·architecture
- output schema
- decision policy
- serving runtime

Compatibility matrix 예:

| input schema | preprocessing | model | output | 지원 |
|---|---|---|---|---|
| v1 | v3 | model-7 | v2 | 지원 |
| v2 | v4 | model-8 | v2 | 지원 |
| v1 | v4 | model-8 | v2 | 변환 adapter 필요 |
| v3 | v3 | model-7 | v2 | 거부 |

### additive change도 자동 호환이 아니다

새 optional field를 추가해도 다음 문제가 생길 수 있다.

- old client가 field를 보내지 않아 분포가 달라진다.
- preprocessing default가 학습 분포와 다르다.
- logging과 privacy policy가 새 field를 처리하지 못한다.

호환성은 contract test로 확인한다.

## 9. latency, throughput와 resource contract

모델 품질과 시스템 비용을 함께 검토한다.

- warm·cold latency
- batch size별 throughput
- memory와 artifact 크기
- CPU/GPU requirement
- 최대 input length
- timeout budget
- concurrency limit
- load 시 초기화 비용

평균만 보고하지 않는다. tail latency와 최악 입력을 본다. 입력 길이에 따라 비용이 비선형으로 증가하는 모델은 length limit과 거부 정책을 둔다.

정확도가 조금 높은 모델이 latency·비용·운영 복잡도 때문에 선택되지 않을 수 있다. 이 판단은 실패가 아니라 제품 계약의 일부다.

## 10. delivery pattern

### offline replay

과거 고정 dataset에서 새 bundle을 실행해 이전 결과와 비교한다.

확인:

- schema 거부율
- prediction difference
- slice별 metric
- resource cost
- 예상치 못한 NaN·극단 score

### shadow

실제 요청을 새 모델에도 전달하지만 action에는 사용하지 않는다. 입력·latency·output 분포를 비교한다. 개인정보와 추가 비용을 고려한다.

### canary

제한된 traffic에 새 version을 적용한다. 사용자 할당이 안정적이어야 하며, model·policy·exposure를 기록한다.

### rollback

다음이 준비돼야 한다.

- 이전 artifact와 runtime
- schema compatibility
- traffic 전환 절차
- 잘못 생성된 prediction·action의 처리
- rollback trigger와 권한

Model file만 되돌리고 decision policy나 feature pipeline은 그대로 두면 실제 이전 상태로 돌아가지 않을 수 있다.

## 11. contract test

### schema test

- 필수 field 누락을 거부한다.
- unknown category 정책을 지킨다.
- NaN·infinite·길이 초과를 처리한다.
- field order가 바뀌어도 이름 기반 입력은 동일하게 처리한다.

### preprocessing parity test

- known fixture의 transformed vector를 고정한다.
- training export와 inference load가 같은 결과를 만든다.
- vocabulary와 label order가 유지된다.

### artifact smoke test

- clean process에서 bundle을 load한다.
- 대표 입력으로 inference한다.
- output schema와 finite value를 확인한다.
- model·schema·policy version을 반환한다.

### compatibility test

지원하는 이전 schema fixture를 실행하고, 지원하지 않는 version은 명시적으로 거부한다.

### performance test

대표·최대 입력에서 latency와 memory를 측정한다. CI의 절대 시간은 환경 차이가 크므로 추세와 별도 controlled benchmark를 구분한다.

## 12. 흔한 실패

### training code를 import해야 inference할 수 있다

불필요한 dependency와 상태가 serving에 들어온다. inference용 최소 package와 bundle loader를 분리한다.

### 모델 weight만 전달한다

feature order·scaler·label map을 잃는다.

### output probability를 바로 action으로 사용한다

비용, capacity, fairness와 정책 변경을 model version에 숨긴다.

### schema 오류를 default zero로 채운다

upstream 장애가 정상 prediction처럼 보인다.

### 새 model과 새 feature pipeline을 동시에 배포한다

장애 원인과 rollback 단위가 모호해진다. 변경을 분리하거나 compatibility 계획을 둔다.

### canary assignment가 요청마다 바뀐다

동일 entity가 서로 다른 정책을 경험하고 outcome 해석이 깨진다.

## 13. release 전 검토

- [ ] inference unit과 observation time이 training row와 맞는다.
- [ ] input schema와 validation policy가 artifact에 있다.
- [ ] fitted preprocessing state와 feature order가 함께 version된다.
- [ ] output score·class·probability의 의미가 명시됐다.
- [ ] decision policy version이 model version과 분리된다.
- [ ] 오류·timeout·partial batch·fallback이 구분된다.
- [ ] clean environment에서 artifact smoke test가 통과한다.
- [ ] supported schema의 compatibility test가 있다.
- [ ] latency·memory·최대 입력 제한을 측정했다.
- [ ] shadow·canary·rollback과 관측 항목이 정해졌다.

## 누적 실습 연결

7단계에서 학습자는 model binary를 반드시 구현할 필요는 없지만, [`model-bundle-manifest.json`](../../exercises/model-lifecycle/templates/model-bundle-manifest.json), [`input-schema.json`](../../exercises/model-lifecycle/templates/input-schema.json)과 [`inference-contract.md`](../../exercises/model-lifecycle/templates/inference-contract.md)를 작성해야 한다. 선택한 library로 실제 artifact를 만들었다면 clean process smoke test와 checksum을 추가한다.
