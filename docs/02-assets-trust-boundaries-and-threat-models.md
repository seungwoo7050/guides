# 자산, 신뢰 경계와 위협 모델

위협 모델은 가능한 공격 이름을 많이 적는 목록이 아닙니다. **보호할 자산, 시스템 경계, 행위자의 capability와 상태 전이**를 연결해 어떤 실패를 먼저 다룰지 결정하는 설계 문서입니다.

## 1. 시스템 context부터 고정하기

먼저 한 문장으로 시스템을 정의합니다.

> 사용자는 공개 HTTPS API에서 자신의 보고서를 생성·조회하며, background worker가 결과를 object storage에 저장합니다.

이 문장에서 최소한 다음 구성요소가 나옵니다.

```text
사용자
공개 gateway
API
worker
database
object storage
identity provider
release pipeline
로그·backup
```

도구 목록보다 사용자 기능과 상태 수명을 먼저 적습니다.

## 2. 범위 안과 밖

context diagram에는 다음을 표시합니다.

- 이번 검토가 소유하는 component
- 외부 provider와 제3자 service
- 실제 운영과 다른 합성 또는 stub 영역
- 변경할 수 없는 legacy component
- 별도 팀이 소유하는 identity·network·backup 경계

범위 밖이라고 해서 위험이 사라지는 것은 아닙니다. 테스트하지 않는다는 뜻이며, 신뢰 가정과 escalation 경로를 남겨야 합니다.

네트워크 topology와 protocol 자체는 `computer-networks`, process·memory·filesystem 격리는 `operating-systems`, 웹 session·HTTP 동작은 `web-app`, 공개 host·배포·backup 운영은 `web-infra`가 정본입니다. 이 장은 그 기반을 다시 가르치지 않고 **어디에서 보안 주장을 다시 검증해야 하는 trust boundary가 생기는지**만 소유합니다. 별도 팀이나 provider가 소유한 경계는 내부 구현을 추측하지 않고 제공된 계약, 현재 evidence, 검증하지 못한 assumption과 연락 경로로 표현합니다.

## 3. 자산 register

자산은 서버 이름만이 아닙니다.

| 분류 | 예 | 보호 질문 |
|---|---|---|
| 업무 데이터 | account, report, payment state | 누가 읽고 바꿀 수 있습니까? |
| identity | user session, service token, signing key | 누가 발급·위임·폐기합니까? |
| 제어권 | DNS, CI, registry, admin API | 탈취되면 어떤 경계를 건너뜁니까? |
| 복구 원본 | source, release manifest, backup | 공격자가 함께 삭제할 수 있습니까? |
| 운영 증거 | audit log, deployment record | 조사 대상이 수정할 수 있습니까? |
| 가용성 자원 | queue capacity, connection pool | 누가 고갈시키고 어떻게 제한합니까? |

각 자산에 다음 필드를 권장합니다.

```text
owner
source of truth
classification
allowed readers
allowed writers
valid states
state transition events
retention
recovery source
security invariant
```

`owner`는 한 이름으로 끝내지 않습니다. [01장의 owner 역할](01-security-state-and-evidence.md#owner를-한-역할로-뭉치지-않기)에 따라 업무·위험 소유자, 상태 정본 소유자, enforcement owner, evidence custodian과 risk acceptance authority를 필요한 만큼 분리합니다. 상태를 만드는 입력, 상태 전이를 승인하는 actor, 실제 경계에서 그 결정을 적용하는 component가 서로 다르면 모두 표시합니다.

## 4. 행위자와 capability

“공격자” 하나로 묶지 않습니다.

- 인증되지 않은 외부 사용자
- 정상 사용자 계정을 가진 악성 사용자
- 탈취된 사용자 session
- 제한된 service token을 가진 workload
- CI job을 수정할 수 있는 contributor
- host의 일반 사용자 권한을 얻은 actor
- 실수한 운영자
- 손상된 dependency 또는 build tool

행위자를 이름보다 capability로 적습니다.

```text
public request 전송 가능
일반 사용자 object ID 관찰 가능
특정 queue에 message 생성 가능
한 repository branch에 push 가능
read-only backup credential 보유
```

## 5. 신뢰 경계

신뢰 경계는 네트워크 subnet과 같지 않습니다. **한 쪽의 주장을 다른 쪽이 추가 검증 없이 믿어서는 안 되는 지점**입니다.

대표 경계:

- browser ↔ API
- gateway ↔ internal service
- user identity ↔ service identity
- application ↔ database
- worker ↔ object storage
- CI ↔ registry
- registry ↔ production runtime
- production ↔ backup storage
- application ↔ audit sink

경계마다 다음을 묻습니다.

1. 누가 누구의 identity를 주장합니까?
2. 어떤 credential과 channel로 증명합니까?
3. 어떤 resource·action scope가 전달됩니까?
4. 실패하면 기본 허용입니까, 기본 거절입니까?
5. decision과 근거가 어디에 기록됩니까?
6. 재시도·cache·proxy가 원래 주장을 바꿀 수 있습니까?

## 6. 데이터 흐름

선 하나에는 하나의 의미만 둡니다.

```text
subject identity 전달
업무 command 전달
artifact 다운로드
secret 발급
audit event 전송
backup 복제
```

흐름에 기록할 항목:

- protocol 또는 transport
- caller와 callee identity
- data classification
- authentication
- authorization decision owner
- integrity·confidentiality protection
- retry·cache·queue semantics
- log·metric·trace evidence

## 7. 위협 문장

다음 형식을 사용합니다.

```text
[capability]를 가진 [actor]가
[entry point]에서 [trust boundary]를 넘을 때
[missing/weak control] 때문에
[asset]의 [security property]를 깨뜨릴 수 있습니다.
```

예:

```text
일반 사용자 session을 가진 actor가
report download route에서 API의 object authorization 경계를 넘을 때
resource owner 검사가 route마다 일관되지 않으면
다른 사용자의 report confidentiality를 깨뜨릴 수 있습니다.
```

이 문장은 payload보다 검증해야 할 상태를 드러냅니다.

### 정상·경계·대표 실패를 함께 모델링하기

위협 문장만 적으면 정상 기능을 보존해야 한다는 계약과 해석이 갈리는 경계 입력이 빠지기 쉽습니다.

| 사례 | report download 예 | 확인할 불변식과 evidence |
|---|---|---|
| 정상 | authenticated owner가 자신의 ready report를 읽음 | 정상 응답이 유지되고 subject·resource·decision이 기록됨 |
| 경계 | 소유권 이전 중, report가 아직 생성 중, owner context 누락, 만료 직전 session | 한 상태 정본과 policy version으로 일관되게 허용·거절하며 불완전 context를 기본 허용하지 않음 |
| 대표 실패 | 일반 사용자가 다른 owner의 identifier를 사용해 내용을 읽음 | 내용과 존재 여부가 노출되지 않고 보호 상태가 변하지 않으며 거절 근거가 남음 |

위협 모델은 실패 입력뿐 아니라 유지해야 할 정상 행동과 경계 해석을 test oracle에 전달해야 합니다. 그래야 이후 patch가 `deny-all`로 보안 테스트만 통과하는 일을 막을 수 있습니다.

## 8. STRIDE와 attack taxonomy의 사용

STRIDE, CWE, CAPEC, ATT&CK 같은 분류는 생각을 넓히는 보조 도구입니다. 시스템 context를 대신하지 않습니다.

- STRIDE는 spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege 관점의 질문을 제공합니다.
- CWE는 구현 약점의 root cause를 정규화하는 데 유용합니다.
- CAPEC은 공격 pattern을 이해하는 데 사용할 수 있습니다.
- ATT&CK은 실제 actor 행동과 탐지 coverage를 연결하는 vocabulary로 사용할 수 있습니다.

분류 항목을 모두 체크했다고 위협 모델이 완성되는 것은 아닙니다.

## 9. 오용 사례와 attack path

단일 위협보다 여러 단계를 연결합니다.

```text
초기 capability
→ 약한 경계
→ 새 identity 또는 data 획득
→ 다음 service의 전제 충족
→ 중요 자산 영향
```

각 edge에 precondition과 postcondition을 적습니다.

| 단계 | precondition | action | postcondition | evidence |
|---|---|---|---|---|
| 1 | 일반 user session | 다른 owner의 report 요청 | report content 획득 가능성 | API response·audit |
| 2 | report metadata | worker job identifier 관찰 | internal object key 추정 | queue·storage log |
| 3 | 과도한 worker scope | object storage read | 대량 report 접근 가능성 | token claim·storage audit |

실제 검증 전에는 “가능성”으로 표시합니다.

## 10. 통제 배치

각 위협에는 prevention만 적지 않습니다.

| 위치 | prevention | detection | recovery |
|---|---|---|---|
| API | 중앙 object authorization | denied·cross-owner attempt event | session revoke, affected object review |
| worker identity | task-scoped token | unusual resource scope usage | token revoke·reissue |
| storage | object prefix policy | cross-prefix read alert | key rotation·access review |

여러 단계 중 한 곳을 막는 것보다 **경로의 여러 독립 지점에서 실패하도록** 설계합니다.

## 11. 가정과 unknown

위협 모델은 모르는 것을 숨기지 않습니다.

```text
ASSUMPTION: gateway가 원본 client identity header를 덮어씁니다.
UNKNOWN: worker token의 실제 production scope는 확인하지 못했습니다.
OUT OF SCOPE: identity provider 내부 MFA 정책은 별도 팀이 소유합니다.
```

가정이 깨지면 어떤 threat가 다시 열리는지 연결합니다.

### 모델과 검증의 한계

context diagram은 component와 선언된 흐름을 보여 주지만 실제 runtime route, hidden dependency, cache·retry와 우회 경로의 부재를 증명하지 않습니다. configuration, 배포 manifest, 실제 호출 trace와 거절 event처럼 서로 다른 근거로 중요한 경계를 확인합니다.

각 edge에는 `hypothesis`, `evidence-supported`, `behavior-verified` 같은 검증 수준과 확인한 version·시간을 기록합니다. 한 edge의 합성 재현은 그 edge의 전제와 postcondition만 지지하며, 앞 단계에서 얻은 identity·data가 다음 단계에 실제로 전달된다는 종단 간 증명은 아닙니다. 반대로 안전 때문에 마지막 영향을 실행하지 않았다면 경로를 `not proven end-to-end`로 남기는 것이 올바른 결과입니다.

## 12. 갱신 trigger

다음 변화가 생기면 threat model을 다시 검토합니다.

- 새 public endpoint 또는 admin 기능
- 새 service·queue·storage
- identity·token·permission 모델 변경
- third-party dependency·provider 추가
- data classification 변경
- deployment·build pipeline 변경
- incident 또는 새로운 vulnerability class 발견
- trust boundary를 건너는 cache·proxy·agent 추가

## 13. 이 장의 산출물

[위협 모델 template](../reference/threat-model-template.md)을 사용해 다음을 작성합니다.

1. 시스템 한 문장
2. context diagram
3. asset register
4. actor와 capability
5. trust boundary와 data flow
6. 위협 문장 8개 이상
7. attack path 2개 이상
8. prevention·detection·recovery mapping
9. assumption·unknown·out-of-scope
10. re-review trigger
11. 정상·경계·대표 실패와 유지해야 할 정상 기능
12. edge별 검증 수준, evidence가 보장하지 않는 범위와 사람 검토 질문

## 14. 완료 질문

- network boundary와 trust boundary는 왜 다를 수 있습니까?
- “외부 공격자”보다 capability를 적는 것이 왜 유용합니까?
- 위협 하나와 attack path는 어떻게 다릅니까?
- 분류 체계를 모두 채워도 놓칠 수 있는 것은 무엇입니까?
- 범위 밖 component의 위험을 어떻게 기록합니까?
- 한 edge를 재현했다는 사실과 전체 attack path를 종단 간 증명했다는 주장은 왜 다릅니까?
- 위협 모델에 정상 사례를 함께 적지 않으면 이후 patch 검증에서 어떤 오류가 생깁니까?
