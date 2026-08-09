# Monitoring, drift와 retraining

배포 시점의 test score는 미래 품질을 보장하지 않는다. 입력 분포, 사용자 행동, 제품 정책, 데이터 수집과 label 생성이 변하면 모델의 의미와 품질도 변한다. Monitoring의 목적은 chart를 많이 만드는 것이 아니라 **어떤 상태 변화가 어떤 위험을 뜻하며, 누가 어떤 action을 수행할지**를 고정하는 것이다.

```text
관측
→ 기준선과 비교
→ 영향 가설
→ 확인할 증거
→ 완화·rollback·재학습 action
→ 결과 검증
```

## 1. 네 층을 분리한다

### 서비스 상태

- 요청 수·오류율
- latency·timeout
- CPU·memory·queue
- artifact load 실패
- dependency availability

이 층은 model quality와 무관하게 inference가 수행되는지를 본다.

### 데이터 상태

- schema 위반
- missing·unknown·범위 초과
- feature freshness
- category vocabulary 변화
- 입력 분포와 상관 구조

### 예측 상태

- score·class·embedding 분포
- abstention·fallback 비율
- threshold별 action volume
- slice별 prediction rate
- model version별 차이

### 결과 품질

- 실제 label 기반 metric
- calibration
- cost·utility
- slice별 오류
- downstream action과 사용자 영향

서비스가 정상이어도 품질이 나쁠 수 있고, prediction 분포가 안정적이어도 label 정의가 바뀔 수 있다.

## 2. monitoring baseline

무엇과 비교하는지 명시한다.

- training distribution
- validation·test distribution
- 직전 안정 운영 기간
- 계절적으로 같은 기간
- control 또는 이전 model
- 사전 정의한 정책 목표

하나의 기준선만 사용하지 않을 수 있다. 주말·월말·지역별 계절성이 강하면 같은 요일·기간과 비교한다.

Baseline artifact에는 다음을 넣는다.

```text
feature별 reference distribution
prediction distribution
slice definition
metric와 threshold
sample size
reference 기간
model·schema·policy version
```

## 3. data quality와 drift

### schema·quality failure

다음은 통계적 drift 이전에 즉시 확인할 수 있다.

- 필수 field 누락
- type·shape 오류
- invalid range
- 중복 row·entity
- timestamp 역전
- category explosion
- freshness 지연

이 문제는 모델 재학습으로 해결하지 않는다. upstream contract와 pipeline을 수정한다.

### covariate shift

입력 `X`의 분포가 변한다.

예:

- 사용자 구성 변화
- 새 product plan
- sensor 교체
- 문서 길이 증가

입력 변화가 곧 품질 저하라는 뜻은 아니다. 모델이 민감한 feature인지, label과 관계가 유지되는지 확인한다.

### prior 또는 label shift

`Y`의 비율이 변한다. threshold와 calibration이 영향을 받을 수 있다.

### concept drift

같은 입력과 label의 관계가 변한다. 사용자 행동, 정책과 경쟁 환경 변화가 원인일 수 있다. 입력 분포만 보고 완전히 탐지하기 어렵고 실제 outcome label이 필요하다.

### measurement drift

현실이 아니라 측정 방식이 바뀐다.

- event logging 변경
- 단위·timezone 변경
- label query 수정
- category mapping 변경

이 경우 새 데이터로 재학습하면 변경된 측정 오류를 학습할 수 있다. 먼저 data contract를 조사한다.

## 4. drift metric의 한계

평균, quantile, missing rate, category frequency와 distance statistic을 사용할 수 있다. 그러나 하나의 숫자를 보편적인 drift 판정기로 사용하지 않는다.

검토:

- sample size가 충분한가?
- 여러 feature를 반복 검사해 false alert가 늘지 않는가?
- 계절성과 정상 campaign을 구분하는가?
- 통계적으로 작아도 운영 영향이 큰 변화인가?
- 통계적으로 커도 모델이 무시하는 feature인가?

Drift alert에는 feature name과 distance뿐 아니라 다음 context를 넣는다.

```text
reference·current 기간
sample count
schema·model version
영향받는 slice
prediction 변화
알려진 product·pipeline 변경
```

## 5. label이 늦게 오는 문제

많은 모델은 예측 직후 정답을 알 수 없다.

예:

- 30일 churn
- 90일 default
- 치료 결과
- 신고·분쟁 확정

따라서 monitoring을 두 시간축으로 나눈다.

### 빠른 proxy

- 입력 quality
- score 분포
- action volume
- feature parity
- 서비스 상태

### 지연 품질

label이 성숙한 cohort만 평가한다.

```text
prediction_time + label_window + reporting_delay
```

아직 label이 완성되지 않은 cohort를 음성으로 취급하면 metric이 왜곡된다. report에는 cohort cutoff와 label maturity를 명시한다.

## 6. calibration과 threshold monitoring

Ranking metric이 유지돼도 probability calibration은 나빠질 수 있다. 다음을 본다.

- probability bucket별 실제 positive rate
- calibration error 또는 Brier score
- threshold 주변 score density
- action capacity와 실제 volume
- slice별 calibration

Base rate가 바뀌면 같은 threshold가 다른 precision을 만든다. Model 재학습 없이 recalibration이나 policy threshold 변경이 가능한지 검토한다. 단, 변경은 validation과 승인 절차를 거친다.

## 7. slice monitoring

전체 평균은 특정 집단의 품질 저하를 숨긴다.

Slice는 다음 기준으로 정할 수 있다.

- 제품·지역·기기·언어
- 데이터 품질 상태
- 신규·기존 사용자
- 입력 길이·범위
- 정책상 중요한 보호 집단

좋은 slice는 사후에 불리한 결과만 골라내는 것이 아니라 사전에 이유와 action을 정한다.

작은 slice는 metric 분산이 크다. count, confidence interval 또는 반복 기간을 함께 보고한다. privacy를 위해 작은 집단을 그대로 노출하지 않는다.

## 8. feedback loop

모델의 prediction이 이후 training data를 바꿀 수 있다.

```text
모델이 위험 사용자를 차단
→ 차단된 사용자의 outcome은 관측되지 않음
→ 다음 dataset에는 허용된 사용자만 남음
```

다른 예:

- 추천이 노출을 바꾼다.
- fraud model이 조사 대상만 label한다.
- 의료 model이 치료를 바꾼다.
- retention offer가 churn outcome을 바꾼다.

이때 운영 label은 자연 발생 outcome이 아니라 정책과 intervention의 결과다. Exposure·action·policy version을 기록하고, 필요한 경우 control·exploration·causal design을 별도로 검토한다.

## 9. alert에서 action으로

Alert마다 owner와 playbook이 있어야 한다.

| 조건 | 확인할 증거 | 가능한 action |
|---|---|---|
| schema reject 급증 | deploy·upstream schema diff | adapter·rollback·traffic 차단 |
| prediction rate 급변 | input·policy·model version | feature 조사·policy rollback |
| latency 초과 | input length·resource·batch | limit·scale·이전 model |
| calibration 악화 | mature label cohort | recalibration·threshold review |
| slice recall 저하 | count·data quality·label | data 조사·model 제한·재학습 |
| 전체 utility 저하 | 비용·capacity·policy | rollback·model selection 재검토 |

Alert만 울리고 action이 없다면 noise가 된다. 반복 false alert는 threshold를 무조건 높이기보다 baseline·seasonality·metric 선택을 다시 검토한다.

## 10. retraining은 자동 정답이 아니다

재학습 전에 원인을 분류한다.

```text
pipeline bug인가?
schema 또는 label 정의가 바뀌었는가?
실제 population이 변했는가?
정책 threshold만 조정하면 되는가?
새 data가 충분히 성숙했는가?
재학습한 model을 독립 평가할 수 있는가?
```

### retraining trigger

- 일정 기간마다 실행
- 충분한 새 label 수
- 품질 또는 calibration 임계값 위반
- product·policy·sensor 변경
- 새로운 class·language·region 지원

시간 기반 자동 재학습은 단순하지만 나쁜 데이터를 자동 확산할 수 있다. Trigger와 release approval을 분리한다.

### training window

- 전체 history
- 최근 sliding window
- 시간 가중치
- 대표 sample과 replay buffer

최근 데이터만 사용하면 rare case와 안정성을 잃을 수 있고, 전체 history는 오래된 관계를 유지할 수 있다. 선택 근거를 평가한다.

## 11. retraining pipeline의 계약

```text
새 data eligibility 확인
→ dataset·split version 생성
→ baseline과 incumbent 재평가
→ candidate 학습
→ validation·slice·robustness 검토
→ final test 또는 release holdout
→ artifact·model card 갱신
→ shadow·canary
→ 승인·rollback 준비
```

Candidate가 이전 model을 이겨야 한다는 단일 규칙은 부족하다. 다음을 함께 본다.

- 핵심 utility
- worst slice
- calibration
- latency·cost
- artifact·schema compatibility
- regression budget
- 운영 복잡도

Incumbent를 새 dataset에서 다시 평가하면 환경 변화와 model 개선을 분리하는 데 도움이 된다.

## 12. rollback과 containment

Rollback trigger 예:

- schema 오류율
- 심각한 slice regression
- action volume 급증
- latency·resource budget 초과
- invalid output
- 안전·정책 위반

Rollback 뒤에도 이미 생성된 prediction과 action은 남을 수 있다. 다음을 설계한다.

- 잘못된 batch output 폐기·재생성
- 영향받은 request·entity 식별
- downstream action 중지
- audit trail 보존
- 원인 수정 전 자동 재배포 금지

## 13. monitoring data 자체의 품질

Monitoring pipeline도 실패한다.

- metric event 누락
- model version tag 누락
- sampling bias
- label join 실패
- timestamp 지연
- dashboard query 변경

따라서 monitor에 대한 monitor가 필요하다.

- expected event count
- label join coverage
- version field completeness
- pipeline freshness
- duplicate rate
- metric code version

`data-engineering`은 이 데이터를 장기간 전달하는 pipeline을 소유하고, 이 브랜치는 어떤 모델 상태와 품질 근거를 수집해야 하는지 소유한다.

## 14. 흔한 실패

### feature drift가 있으면 즉시 재학습한다

원인이 schema bug인지 실제 변화인지 모른다.

### 전체 accuracy만 본다

Base rate, threshold, calibration과 slice regression을 놓친다.

### label이 덜 성숙한 최근 cohort를 평가한다

음성 비율과 품질을 왜곡한다.

### model version만 기록한다

schema·preprocessing·policy·exposure가 달라진 원인을 추적하지 못한다.

### alert threshold에 action이 없다

운영자가 매번 의미를 새로 판단해야 한다.

### 재학습 결과를 자동 배포한다

나쁜 data·label bug·호환성 regression이 release된다.

## 15. monitoring plan 체크리스트

- [ ] 서비스·데이터·예측·결과 품질을 분리했다.
- [ ] 각 metric의 reference 기간·sample·version이 있다.
- [ ] label window와 maturity cutoff가 명시됐다.
- [ ] calibration과 action threshold를 모니터링한다.
- [ ] 중요한 slice와 최소 sample 정책이 있다.
- [ ] model이 만든 feedback loop를 기록한다.
- [ ] alert마다 owner·evidence·action·severity가 있다.
- [ ] retraining trigger와 release approval이 분리됐다.
- [ ] incumbent와 candidate를 같은 새 dataset에서 비교한다.
- [ ] rollback 뒤 downstream 결과 처리 절차가 있다.
- [ ] monitoring pipeline의 completeness와 freshness를 검사한다.

## 누적 실습 연결

8단계에서 [`monitoring-plan.md`](../../exercises/model-lifecycle/templates/monitoring-plan.md)를 작성한다. 최소한 service·data·prediction·delayed quality metric, baseline, alert owner, action, label maturity, retraining trigger와 rollback을 포함한다. 실제 운영 metric을 수집하지 않더라도 어떤 event와 version tag가 필요한지 구체적으로 설계한다.
