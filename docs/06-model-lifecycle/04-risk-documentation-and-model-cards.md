# 위험 관리, 문서화와 model card

모델 개발의 최종 결과는 점수와 weight가 아니다. **누가 어떤 목적으로 사용할 수 있고, 어떤 데이터와 평가가 그 사용을 지지하며, 어디서 실패하고, 문제가 생기면 어떻게 제한·중단할지**를 전달해야 한다.

Model card는 이 정보를 구조화하는 한 형식이다. 문서를 작성했다고 모델이 안전하거나 공정해지는 것은 아니다. 문서는 근거·결정·미해결 위험을 드러내 검토와 운영 action을 가능하게 한다.

## 1. 위험을 모델 내부에만 한정하지 않는다

위험은 전체 시스템에서 발생한다.

```text
사용 목적과 사용자
+ data 수집·label
+ model과 threshold
+ UI·업무 절차
+ 자동 action
+ monitoring·appeal·rollback
```

예를 들어 같은 score라도 다음 시스템은 위험이 다르다.

- 사람이 추가 조사할 대상을 정하는 보조 도구
- 사용자 계정을 자동 차단하는 시스템
- 자원 배분 우선순위를 추천하는 시스템
- 의료·금융·고용 결정을 자동화하는 시스템

모델의 role과 인간의 실제 통제 가능성을 명확히 한다. “human in the loop”라는 문구만으로 통제가 존재하지 않는다. 사람이 충분한 정보·시간·권한을 갖는지 본다.

## 2. intended use

다음 질문에 답한다.

- primary user는 누구인가?
- prediction subject는 누구 또는 무엇인가?
- 어떤 action을 지원하는가?
- 어느 환경·지역·언어·시간 범위를 가정하는가?
- 어떤 입력과 최소 품질이 필요한가?
- 사람이 검토하는가, 자동 action인가?
- outcome을 언제 확인할 수 있는가?

좋은 intended use 예:

```text
최근 90일 사용 이력이 있는 구독 고객에 대해 30일 내 자발적 해지 가능성을 추정한다.
점수는 retention 담당자가 연락 후보를 우선순위화할 때만 사용한다.
계정 제한, 가격 차별 또는 계약 해지 자동화에는 사용하지 않는다.
```

“churn 예측에 사용”은 너무 넓다.

## 3. out-of-scope와 금지된 사용

금지된 사용은 단순 면책 문구가 아니라 입력 validation, access policy, UI와 감사 절차에 연결한다.

예:

- 학습·평가에 포함되지 않은 국가·언어
- 미성년자 또는 특정 보호 집단에 대한 결정
- 개인에게 불이익을 주는 자동 action
- 실시간 safety-critical 제어
- 법률·의료 판단의 대체
- 다른 label 의미로 재사용

범위를 벗어난 입력을 기술적으로 식별할 수 없다면 그 한계를 기록하고 운영 검토를 추가한다.

## 4. 이해관계자와 피해

### 이해관계자

- 모델을 개발·운영하는 팀
- prediction을 사용하는 실무자
- prediction subject
- 잘못된 action의 영향을 받는 사람
- data를 제공한 사람과 조직
- 감사·규제·보안 담당자

### 피해 유형

- false positive·false negative의 직접 비용
- 서비스 접근 제한
- 과도한 감시·연락
- 집단별 불균형
- 개인정보 노출
- automation bias와 책임 회피
- feedback loop로 인한 장기 왜곡
- 공격자가 score 또는 model을 악용하는 위험

Metric은 피해의 proxy일 뿐이다. 각 오류가 실제 workflow에서 어떤 action을 만드는지 연결한다.

## 5. data와 평가 근거

Model card는 dataset card와 연결한다.

기록할 내용:

- data source와 수집 기간
- 포함·제외 기준
- observation unit과 label window
- sample·split 정책
- 누출 검사
- 대표성이 약한 집단
- missing·measurement error
- privacy·consent·retention 제한

평가에는 다음을 포함한다.

- baseline
- selection metric과 이유
- final test 결과
- threshold와 비용 가정
- calibration
- 중요 slice
- confidence·sample size
- stress·shift·robustness 검사
- 평가하지 못한 조건

최고 점수만 쓰지 않는다. 어떤 주장을 지지하지 못하는지도 적는다.

## 6. fairness와 slice 평가

공정성을 하나의 metric으로 정의하지 않는다. 문제에 따라 다음 질문이 다르다.

- 어떤 집단에 false positive가 더 위험한가?
- label 자체가 과거 차별이나 선택 편향을 반영하는가?
- 보호 attribute를 feature에서 빼도 proxy가 남는가?
- threshold를 동일하게 적용하는 것이 타당한가?
- 데이터가 적은 집단의 불확실성을 어떻게 처리하는가?
- 모델 사용이 자원과 기회를 어떻게 바꾸는가?

Slice 결과가 나쁘다고 집단별 모델이나 threshold를 자동 적용하지 않는다. 법적·윤리적·제품적 의미와 운영 가능성을 검토한다.

이 브랜치는 평가 질문과 근거 기록을 다룬다. 특정 법률 준수 판단은 자격 있는 법률·정책 전문가의 검토가 필요하다.

## 7. privacy와 data governance

Model artifact와 training data에는 민감한 정보가 남을 수 있다.

- 직접 식별자
- rare category와 memorization
- embedding 또는 gradient의 정보 노출
- experiment log의 raw row
- 삭제 요청과 재학습 관계
- data retention과 access control

Model card에 다음을 연결한다.

- 허용 data purpose
- access owner
- retention·deletion 정책
- 민감 feature 사용 이유
- logging redaction
- data 또는 model 삭제·교체 절차

상세 보안 통제는 `cybersecurity`와 운영 플랫폼이 소유하지만, 모델 개발자는 필요한 data와 artifact 경계를 식별해야 한다.

## 8. security와 misuse

모델은 공격 대상이거나 공격 도구의 일부가 될 수 있다.

- artifact 변조
- 신뢰하지 않는 serialization load
- model extraction
- membership·training data inference
- adversarial input
- data poisoning
- 생성 모델의 위험 출력
- 과도한 capability 공개

모든 공격을 이 브랜치에서 구현하지 않는다. Model card에는 위협 가정, 접근 범위, 알려진 검사와 미검사 영역을 기록한다.

## 9. limitation을 구체적으로 쓴다

나쁜 예:

```text
모델은 완벽하지 않으며 주의해서 사용해야 한다.
```

좋은 limitation은 조건과 관찰 가능한 결과를 포함한다.

```text
training data에는 가입 후 3개월 미만 사용자가 적다. 해당 slice의 recall 추정치는 표본이 작아 불안정하다. 신규 사용자는 자동 retention action에서 제외하고 월별 label이 500건 이상 쌓일 때 다시 평가한다.
```

다음 종류를 검토한다.

- data coverage
- temporal·geographic shift
- measurement·label noise
- threshold·calibration
- slice uncertainty
- latency·resource limit
- explainability 한계
- 인간 검토의 실제 한계
- feedback loop

## 10. release decision

Model card는 승인 여부를 대신하지 않는다. Release review는 다음 선택 중 하나를 명시한다.

```text
approve
조건과 범위 안에서 배포

approve with controls
수동 검토·traffic 제한·추가 monitoring 등 조건부 승인

defer
필수 근거 또는 통제가 부족해 보류

reject
현재 use case에는 위험이 수용 불가능
```

Decision record에는 다음이 있다.

- 승인 대상 artifact·schema·policy version
- 검토한 evidence
- unresolved risk
- 필수 control
- owner와 재검토 날짜
- rollback condition

## 11. model card 권장 구조

### 1. Model details

- 이름·version·owner
- artifact digest
- model family와 주요 dependency
- release date와 status

### 2. Intended use

- primary use
- user와 subject
- supported environment
- human review와 action

### 3. Out-of-scope use

- 금지·미지원 사용
- 입력 범위 밖 조건

### 4. Training data

- dataset card 링크
- 기간·sample·split
- feature와 label 계약

### 5. Evaluation

- baseline·metric·threshold
- test·slice·calibration
- stress·shift 검사

### 6. Limitations and risks

- known failure
- uncertainty
- privacy·fairness·security·misuse

### 7. Operational controls

- schema validation
- monitoring·alert
- human review·appeal
- rollout·rollback

### 8. Change history

- 이전 version과 차이
- migration·compatibility
- 재평가가 필요한 변경

## 12. 문서의 수명

Model card는 release 때 한 번 쓰고 끝나는 문서가 아니다. 다음 사건에서 갱신한다.

- dataset·label·split 변경
- model·preprocessing 변경
- threshold·policy 변경
- 새 지역·언어·집단 지원
- 중요한 incident
- monitoring에서 새 limitation 발견
- dependency·artifact format 변경

과거 card를 덮어쓰지 않고 release version과 함께 보존한다.

## 13. 문서와 통제의 연결

| 문서 주장 | 시스템 통제 예 |
|---|---|
| 지원하지 않는 category | schema validation·reject metric |
| 자동 차단 금지 | authorization·workflow restriction |
| 수동 검토 필요 | review queue·actor log |
| 낮은 confidence에서 abstain | decision policy |
| 월별 calibration 검토 | scheduled report·owner |
| 심각한 drift 시 rollback | alert·runbook·artifact retention |

문서가 시스템과 다르면 시스템 동작이 사실이다. 문서와 실제 통제를 함께 테스트한다.

## 14. 흔한 실패

### template을 채우는 것이 목표가 된다

근거 없는 일반 문구가 늘고 중요한 위험이 숨는다.

### 모델 팀만 작성한다

실제 사용자·subject·운영·정책 관점이 빠진다.

### 성능이 낮은 slice를 삭제한다

지원 범위를 축소하거나 control을 추가하지 않고 report만 정리한다.

### model version은 있지만 policy version이 없다

같은 score가 다른 action을 만든 원인을 추적하지 못한다.

### limitation이 action과 연결되지 않는다

알려진 위험이 운영에서 그대로 발생한다.

### 배포 뒤 card를 갱신하지 않는다

현재 artifact와 문서가 분리된다.

## 15. release review 체크리스트

### 목적과 책임

- [ ] primary user·subject·action이 구체적이다.
- [ ] 자동화 수준과 인간 권한이 실제 workflow와 일치한다.
- [ ] out-of-scope use가 기술·운영 통제와 연결된다.

### 근거

- [ ] dataset card와 split·label version을 가리킨다.
- [ ] baseline·test·threshold·calibration과 slice 결과가 있다.
- [ ] 표본과 불확실성, 평가하지 않은 조건이 보인다.

### 위험

- [ ] false positive·negative의 실제 영향을 설명한다.
- [ ] privacy·fairness·security·feedback loop를 검토했다.
- [ ] limitation마다 owner 또는 control이 있다.

### 운영

- [ ] monitoring·incident·appeal·rollback 경로가 있다.
- [ ] model·schema·preprocessing·policy version이 연결된다.
- [ ] 재검토 조건과 문서 갱신 책임이 정해졌다.

## 누적 실습 연결

8단계에서는 [`model-card.md`](../../exercises/model-lifecycle/templates/model-card.md)와 monitoring plan을 작성한다. “합성 데이터이므로 위험 없음”이라고 쓰지 않는다. 합성 문제에서도 intended use, 금지된 자동 action, false positive·negative, 부족한 slice, label delay, rollback과 실제 데이터로 이동할 때 필요한 추가 검토를 구체적으로 남긴다.
