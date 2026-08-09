# Capstone C: Model release review

이 capstone은 새 모델을 직접 만드는 대신 **다른 팀이 제출한 release candidate를 검토하는 상황**을 다룬다. 모델 개발자는 자신의 실험을 설명하는 능력뿐 아니라 누락된 근거, 호환성·운영 위험과 잘못된 평가를 발견하는 능력이 필요하다.

## 1. 입력

검토 대상은 다음 묶음이다.

```text
problem contract
dataset card와 split manifest
experiment records
candidate evaluation
model bundle
input·output schema
inference contract
model card
monitoring·rollback plan
```

실제 binary model은 선택이다. 제공되지 않았다면 release 준비 상태를 그에 맞게 판단한다.

## 2. 역할

학습자는 release reviewer다. 다음 선택 중 하나를 근거와 함께 내린다.

```text
APPROVE
지정된 범위와 control에서 release 가능

APPROVE WITH CONDITIONS
명시한 control·monitoring·traffic 제한을 적용할 때만 가능

DEFER
결정에 필요한 근거 또는 artifact가 부족함

REJECT
현재 use case와 위험에서 release하면 안 됨
```

목표는 모든 항목을 비판하는 것이 아니라 **실제 결정에 영향을 주는 blocker와 non-blocker를 구분하는 것**이다.

## 3. 검토 순서

### 1. 문제와 action

- prediction subject·observation time·label window가 명확한가?
- model output이 어떤 action을 바꾸는가?
- false positive·negative의 실제 영향이 설명됐는가?
- intended·out-of-scope use가 구체적인가?

문제가 잘못 정의되면 model architecture를 검토할 필요가 없다.

### 2. data와 split

- dataset provenance와 포함 기준이 있는가?
- label을 prediction time에 사용할 수 있는 정보만으로 생성했는가?
- entity·time·group 경계가 deployment를 모사하는가?
- test가 model selection에 사용되지 않았는가?
- 중요한 slice와 대표성 한계가 있는가?

### 3. baseline과 evaluation

- trivial·rule·incumbent baseline이 있는가?
- metric이 action 비용과 capacity에 연결되는가?
- threshold가 validation에서 선택됐는가?
- calibration과 sample size를 보는가?
- 평균이 중요한 slice regression을 숨기지 않는가?
- 여러 run·seed·comparison으로 인한 과적합을 고려했는가?

### 4. artifact와 inference

- model·preprocessing·schema·label map이 같은 bundle인가?
- clean process에서 load·smoke test가 가능한가?
- output 의미와 policy version이 명확한가?
- invalid input·timeout·fallback·partial batch가 정의됐는가?
- 이전 version과 compatibility·rollback 경로가 있는가?

### 5. 운영과 위험

- service·data·prediction·delayed quality monitoring이 있는가?
- label maturity를 고려하는가?
- alert에 owner와 action이 있는가?
- feedback loop와 human review가 실제로 기록되는가?
- known limitation에 control이 연결되는가?

## 4. blocker 분류

### 즉시 blocker 예

- train/test leakage
- test 기반 model·threshold 선택
- artifact와 preprocessing 불일치
- unsupported input이 자동 coercion돼 위험한 action 생성
- rollback 불가능한 destructive 자동 action
- intended use에 필요한 집단의 평가 부재
- model card의 artifact version 불일치

### 조건부 blocker 예

- 작은 slice의 불확실성
- latency 측정 부족
- 일부 compatibility fixture 누락
- monitoring threshold 조정 필요

Traffic 제한, 수동 검토, shadow 기간과 추가 검증으로 완화할 수 있는지 본다.

### non-blocker 예

- 문서 표현 개선
- release와 무관한 미래 architecture 제안
- 현재 범위 밖 기능 요청
- metric에 영향을 주지 않는 report format 차이

중요도를 혼동하지 않는다.

## 5. review report 구조

```markdown
# Release review

## Decision
APPROVE | APPROVE WITH CONDITIONS | DEFER | REJECT

## Reviewed versions
- model:
- dataset:
- split:
- schema:
- preprocessing:
- policy:

## Supported claim
현재 evidence가 지지하는 주장을 한 문단으로 제한

## Blocking findings
각 항목에 evidence, impact, required action

## Non-blocking findings
후속 개선과 owner

## Required controls
traffic, manual review, monitoring, rollback

## Revalidation
어떤 변경이 생기면 무엇을 다시 평가할지
```

## 6. 최소 증거 표

| 주장 | 필요한 증거 | 상태 |
|---|---|---|
| 새 고객에 일반화 | entity-disjoint test | 확인·부족 |
| review workload 안에서 recall 개선 | budget 기반 validation·test | 확인·부족 |
| probability 사용 가능 | calibration evidence | 확인·부족 |
| input 호환 | schema·contract tests | 확인·부족 |
| rollback 가능 | 이전 bundle·runbook | 확인·부족 |
| 운영 품질 추적 | mature label monitoring | 확인·부족 |

모든 주장은 artifact나 실행 결과로 추적할 수 있어야 한다.

## 7. 변경 시 재평가 범위

### model weight만 변경

- validation·test·slice·calibration
- performance와 artifact smoke

### feature·preprocessing 변경

- leakage·availability
- schema·offline-online parity
- compatibility
- 전체 model evaluation

### threshold·policy 변경

- action volume·cost·slice 영향
- model metric 일부는 재사용 가능하나 실제 decision 결과를 다시 검토

### label 정의 변경

- problem contract·dataset·baseline·모든 평가를 재검토

### 새 지역·언어·사용자 집단

- data coverage와 해당 slice 평가
- intended use와 model card 갱신

## 8. 완료 기준

- [ ] 결과보다 먼저 problem·data·split을 검토했다.
- [ ] blocker와 개선 제안을 구분했다.
- [ ] 각 finding에 evidence와 영향이 있다.
- [ ] 승인 범위와 금지 범위를 명시했다.
- [ ] model뿐 아니라 schema·preprocessing·policy version을 확인했다.
- [ ] monitoring·rollback과 delayed label을 검토했다.
- [ ] 재평가가 필요한 변경 범위를 정했다.
- [ ] 모르는 영역을 근거 없이 승인하거나 거부하지 않았다.

## 9. 실제 프로젝트로 확장

오픈소스 model repository나 작은 내부 project에서 다음 작업으로 이어갈 수 있다.

- 기존 evaluation script의 split·metric 검토
- dataset card·model card 개선
- artifact loader와 compatibility test
- deterministic fixture와 smoke test
- training config provenance
- slice·calibration report
- rollback·monitoring 설계 문서

실제 조직의 release 권한과 법적·안전 기준은 프로젝트 정책을 따른다.
