# 보안 telemetry, 탐지와 조사

탐지는 공격 이름을 log에서 찾는 일이 아닙니다. 위협 모델의 상태 전이가 일어날 때 **어떤 event가 남고, 어떤 sequence가 정상과 다르며, 조사자가 어떤 사실을 재구성할 수 있는지**를 설계하는 작업입니다.

## 1. security telemetry의 목적

- 중요한 allow·deny decision 재구성
- identity·permission·configuration 변경 추적
- attack-path edge의 시도와 성공 구분
- incident scope와 affected asset 확인
- containment·recovery가 실제 적용됐는지 확인
- control failure·logging gap 감지

모든 debug log를 많이 저장하는 것이 목적이 아닙니다.

## 2. event schema

보안 decision event에 필요한 기본 필드:

```text
event_time·timezone·clock quality
ingest_time
source service·instance·version
event type
request·trace·job ID
subject identity·type·session
actor와 delegated subject
source network·device context
action
resource type·ID·tenant
policy decision·reason
result·status
credential or policy version
release digest
```

민감한 body·token·secret을 그대로 기록하지 않습니다. 조사에 필요한 식별자와 결정을 구조화합니다.

### 서로 다른 시간

- `event_time`은 source가 action·decision을 관찰한 시각입니다.
- `ingest_time`은 첫 trusted collector가 event를 받아들이며 envelope에 추가한 시각입니다.
- `discovery_time`은 analytic이나 조사자가 조건을 처음 식별한 시각이며 alert·case metadata에
  기록합니다.

세 시각은 서로 대체할 수 없습니다. `ingest_time - event_time`은 수집 지연과 clock skew가
섞인 값이고, `discovery_time - event_time`은 수집·분석·queue 지연을 함께 포함합니다.
UTC offset, clock source·오차, timestamp precision, source sequence를 보존하고 음수 지연이나
out-of-order event를 무조건 폐기하지 않습니다.

### privacy와 최소 수집

각 field에 조사 목적, 접근 역할, 보존 기간, 삭제·legal hold 규칙을 둡니다. raw token,
request body, 불필요한 개인 데이터는 수집 전에 제거하고, pseudonymous ID도 다른 정보와
결합해 사람을 식별할 수 있으면 보호 대상입니다. hash만 했다고 자동으로 익명 데이터가
되지는 않습니다. 보안 조사의 linkability와 data minimization 사이의 선택을 문서화합니다.

## 3. allow event와 deny event

거절만 기록하면 성공한 악용과 정상 access를 비교하기 어렵습니다. 모든 read를 무제한 기록하면 비용·privacy 문제가 생깁니다.

위험과 자산에 따라 선택합니다.

- admin·privileged action은 allow·deny 모두 기록
- sensitive export·download는 allow 기록
- 반복되는 low-risk read는 sampling 또는 aggregate
- policy·credential·release 변경은 항상 기록
- log configuration·deletion 시도는 별도 중요 event

## 4. identity chain

다중 service에서는 다음을 구분합니다.

```text
human/user actor
upstream service
current workload identity
delegated subject
token issuer·audience·scope
```

모든 action을 service account 하나로 기록하면 원래 actor와 resource context를 잃습니다.

## 5. detection hypothesis

좋은 analytic은 공격 이름보다 관찰 가능한 가설에서 시작합니다.

```text
THREAT
일반 user session이 여러 owner의 report ID를 탐색할 수 있음

HYPOTHESIS
짧은 시간에 한 subject가 여러 owner의 report에 대해 반복 deny를 만들거나,
평소 접근하지 않던 tenant의 successful read를 생성함

DATA
policy decision, subject, resource owner, tenant, result, request ID

ANALYTIC
deny diversity + unexpected successful cross-owner decision

TRIAGE
account 정상 workflow, support action, batch job, policy version 확인
```

## 6. sequence와 graph

단일 event가 정상처럼 보여도 sequence는 비정상일 수 있습니다.

```text
new session
→ resource discovery 증가
→ denied requests
→ service token issue
→ unusual storage reads
→ audit configuration change
```

request·trace·job·identity·resource ID로 event를 연결합니다. clock skew와 missing event를 고려합니다.

## 7. ATT&CK의 사용

ATT&CK은 실제 관찰 기반 adversary behavior의 vocabulary로 사용할 수 있습니다.

- threat model의 behavior와 technique 연결
- 필요한 data source 확인
- detection coverage gap 정리
- simulation·purple-team scenario 설계

이 가이드의 2026-08-09 기준 판본인 [ATT&CK v19.2](https://attack.mitre.org/resources/versions/)에서는 다음 층을 구분합니다. living catalog이므로 사용 시점의 판본과 domain을 함께 기록하고 minor update에도 mapping을 재검토합니다.

```text
technique: 공격자가 보이는 behavior
→ detection strategy: 그 technique를 찾는 상위 접근
→ analytic: platform·log source별 구체적 탐지 논리
→ data component: analytic에 필요한 관찰 종류
```

detection strategy는 여러 platform-specific analytic을 묶는 container입니다. ATT&CK analytic의
field·threshold를 자신의 환경에 그대로 복사한다고 검증되는 것은 아닙니다. 사용한 ATT&CK
판본·object permalink, 현지 event schema로의 mapping, 변경한 mutable element와 검증 fixture를
기록합니다. matrix cell을 많이 채우는 것이 coverage가 아닙니다. 자신의 system에서 해당
behavior가 가능한지, 필요한 data component가 실제 수집되는지, 구현한 analytic이
known-positive·negative에서 검증됐는지가 중요합니다.

## 8. alert quality

평가할 항목:

- precision: 정한 label과 모집단에서 `TP / (TP + FP)`
- recall: 같은 모집단에서 `TP / (TP + FN)`
- labeled incident가 부족하면 known-scenario detection rate를 별도 이름으로 보고
- detection latency
- data freshness·completeness
- duplicate·storm behavior
- owner와 on-call routing
- triage time과 필요한 context
- failure mode와 health monitoring

alert가 많다는 사실은 탐지가 좋다는 증거가 아닙니다.

precision과 recall에는 ground truth, 관찰 기간, sampling·suppression, label 기준이 필요합니다.
운영에서 발견하지 못한 공격 전체를 알 수 없다면 recall을 직접 측정했다고 주장하지
않습니다. known-positive fixture 중 탐지 비율은 regression 근거이지 운영 recall이 아니며,
known-negative fixture 통과도 실제 false-positive rate를 대신하지 않습니다.

## 9. false positive와 false negative

### false positive 원인

- legitimate batch·support workflow
- shared account
- clock·identity mapping 오류
- deployment·migration change
- threshold가 environment와 맞지 않음

### false negative 원인

- 필요한 event field 누락
- allow decision 미수집
- attacker가 다른 identity·slow rate 사용
- log pipeline 지연·drop
- analytic이 하나의 path만 가정
- privileged actor를 allowlist로 제외

예외를 늘리기 전에 event schema와 identity model을 검토합니다.

## 10. log integrity와 availability

- application이 local file을 지울 수 있습니까?
- audit sink가 별도 identity·storage를 사용합니까?
- event loss·backlog·parser failure를 알 수 있습니까?
- timestamp source와 sequence가 있습니까?
- retention이 incident discovery delay보다 충분합니까?
- privacy·access·deletion policy가 있습니까?

공격자가 log를 지우지 않아도 pipeline 장애로 evidence가 사라질 수 있습니다.

## 11. detection-as-code

analytic, test fixture, expected result와 version을 함께 관리합니다.

```text
rule ID
threat·requirement mapping
required fields
query or logic
threshold·window
known benign cases
expected test alerts
owner
rollout·rollback
last validated
```

known-positive·known-negative fixture로 변경을 검증합니다.

## 12. triage packet

alert가 조사자에게 다음을 제공해야 합니다.

- 왜 발생했는가?
- 어떤 threat·asset과 관련되는가?
- subject·resource·time range는 무엇인가?
- 앞뒤 event를 어디서 찾는가?
- 즉시 중단해야 할 조건은 무엇인가?
- 정상 workflow로 판정하려면 어떤 owner에게 확인하는가?
- containment가 필요한 경우 어떤 runbook을 사용하는가?

## 13. 이 장의 산출물

[탐지 설계 실습](../exercises/05-detection-engineering/README.md)에서 threat 3개를 골라 다음을 작성합니다.

1. event schema
2. detection hypothesis
3. analytic logic
4. known-positive·negative fixture
5. triage packet
6. false positive·negative 분석
7. log pipeline health control
8. ATT&CK mapping과 한계
9. event·ingest·discovery time과 privacy·retention 계약
10. precision·recall 또는 대체 지표의 모집단·label·한계

## 14. 완료 질문

- debug log를 많이 남기는 것과 security telemetry는 어떻게 다릅니까?
- service identity만 기록하면 어떤 조사 정보가 사라집니까?
- ATT&CK technique mapping이 detection coverage를 자동 증명하지 않는 이유는 무엇입니까?
- allow event가 필요한 경우는 언제입니까?
- analytic 자체와 log pipeline health를 모두 감시해야 하는 이유는 무엇입니까?
- known-scenario detection rate를 운영 recall이라고 부를 수 없는 이유는 무엇입니까?
- event time, ingest time, discovery time이 각각 필요한 이유는 무엇입니까?
