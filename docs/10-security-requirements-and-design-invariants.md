# 보안 요구사항과 설계 불변식

위협 모델은 가능한 실패를 설명합니다. 보안 요구사항은 **시스템이 그 실패를 어떻게 거부·제한·기록·복구해야 하는지**를 검증 가능한 문장으로 바꿉니다.

## 1. 좋은 요구사항의 형태

다음 문장은 너무 넓습니다.

> API는 안전해야 합니다.

다음처럼 바꿉니다.

```text
REQ-AUTHZ-003
모든 report read는 authenticated subject, requested action,
report owner와 tenant를 policy decision에 포함해야 합니다.
foreign owner 또는 tenant인 경우 report 존재 여부를 불필요하게 노출하지 않고 거절하며,
subject·resource·decision·reason이 audit event에 남아야 합니다.
```

검증 가능한 요구사항은 다음을 포함합니다.

- subject
- object 또는 asset
- action
- context·precondition
- 허용·거절·격리 결과
- 필요한 evidence
- failure behavior

## 2. threat에서 requirement로 변환하기

```text
Threat
일반 user session을 가진 actor가 다른 owner의 report ID를 사용해
confidentiality를 깨뜨릴 수 있음

Invariant
report read는 subject-resource ownership을 항상 검사함

Requirement
모든 read path는 중앙 policy를 호출하고 foreign owner를 거절함

Test
owner·other owner·other tenant·revoked subject matrix

Detection
cross-owner denied attempt event와 반복 pattern alert

Recovery
영향 session revoke, access review, affected object scope 확인
```

하나의 threat가 여러 requirement를 만들 수 있고, 하나의 requirement가 여러 threat를 줄일 수 있습니다.

threat 수준의 문장만으로 coverage를 선언하지 않습니다. 같은 threat도 API read, export,
background worker처럼 서로 다른 attack path를 가질 수 있기 때문입니다. 각 path에서 어떤
state transition을 prevention이 거절하고, 어떤 event를 detection이 관찰하며, 훼손된 신뢰와
상태를 recovery가 어떻게 복원하는지 따로 연결합니다.

| Attack path | Prevention | Detection | Recovery | 적용 상태와 근거 |
|---|---|---|---|---|
| direct report read | ownership policy | cross-owner deny·unexpected allow | session revoke·scope 조사 | applicable: API integration test |
| export worker | job-scoped token | foreign prefix access event | token rotate·derived export 폐기 | applicable: worker fixture |
| legacy batch | 중앙 policy 적용 여부 조사 | legacy identity 사용 관찰 | 영향 batch output 검증 | unknown: owner·확인 기한 |

`N/A`는 control을 구현하지 않았다는 뜻이 아닙니다. 해당 path에서 requirement의 전제가
성립할 수 없음을 architecture·configuration·실행 evidence로 보이고, 그 판단의 owner와
re-review trigger를 기록할 때만 사용합니다. 확인하지 못한 path는 `N/A`가 아니라
`unknown` 또는 `not tested`입니다.

## 3. prevention·detection·recovery requirement

보안 requirement를 prevention에만 두지 않습니다.

세 종류의 역할은 다릅니다. prevention은 위험한 state transition을 막거나 제한하고,
detection은 이미 일어난 시도·성공·control failure를 관찰하며, recovery는 영향을 받은
identity·data·artifact의 신뢰를 다시 세웁니다. alert와 monitoring은 공격자의 capability를
제거하지 않으므로 그 자체로 containment나 recovery가 아닙니다.

### Prevention

- unauthorized state transition 거절
- least privilege와 scope 제한
- untrusted data와 interpreter 분리
- artifact·identity 검증
- resource budget

### Detection

- 중요한 allow·deny decision 기록
- privilege·scope·configuration 변경 audit
- expected sequence에서 벗어난 상태 관찰
- log 손실·지연·변조 감지

### Recovery

- credential revoke·rotate
- trusted artifact로 rebuild
- data restore와 integrity validation
- session·cache·derived data invalidation
- incident communication과 재검토

## 4. fail-safe default

기본값을 명시합니다.

- policy service timeout이면 allow입니까, deny입니까?
- audit sink 장애면 업무를 계속합니까?
- certificate·signature verification이 불가능하면 배포합니까?
- dependency advisory feed가 unavailable이면 release를 멈춥니까?
- detection rule이 실패하면 누가 알 수 있습니까?

모든 경우 무조건 fail-closed가 정답은 아닙니다. 안전·가용성·복구 비용을 함께 검토하고 어떤 위험을 선택했는지 적습니다.

## 5. 최소 권한 requirement

“최소 권한을 적용합니다”를 다음처럼 구체화합니다.

```text
worker token은 audience=object-store이고,
job의 tenant와 report prefix에 대한 read·write만 허용하며,
10분 뒤 만료되고,
admin API와 backup storage에는 사용할 수 없어야 합니다.
```

test:

- intended prefix allow
- other tenant prefix deny
- unrelated API deny
- expired token deny
- wrong audience deny
- revoke 뒤 deny

## 6. secure default와 사용성

사용자가 별도 hardening 문서를 읽어야만 안전한 제품보다 안전한 기본값을 제공합니다.

- admin interface는 기본 public exposure 금지
- debug·verbose error는 production 기본 비활성화
- new tenant·resource는 기본 private
- dependency·artifact verification은 release 기본 gate
- broad permission은 명시적 exception 필요
- security logging은 중요한 decision에서 기본 활성화

안전한 기본값이 실제 업무를 불가능하게 만들면 사용자가 우회할 수 있습니다. 필요한 workflow와 함께 설계합니다.

## 7. requirement owner

각 requirement에는 owner가 필요합니다.

| 종류 | owner 예 |
|---|---|
| object authorization | application team |
| workload token scope | platform·identity team |
| storage policy | storage owner |
| release provenance | build·release owner |
| detection analytic | security operations |
| restore integrity | operations·data owner |

여러 팀에 걸치면 각 control과 evidence의 owner를 나눕니다.

여기서 owner라는 단어를 하나의 역할로 뭉치지 않습니다.

- 업무·위험 owner는 보호할 결과와 impact를 설명합니다.
- 상태 정본 owner는 asset·identity·finding의 authoritative state를 관리합니다.
- enforcement owner는 policy와 실패 동작을 구현·운영합니다.
- evidence custodian은 log·test·artifact의 보존과 접근을 책임집니다.
- risk acceptance authority는 조직이 정한 권한으로만 예외를 승인합니다.

한 사람이 여러 역할을 맡을 수 있지만 requirement에는 어떤 역할로 결정했는지 적습니다.
security reviewer가 evidence를 평가했다는 사실만으로 risk acceptance authority가 되지는
않습니다.

## 8. requirement ID와 traceability

권장 chain:

```text
THR-REPORT-02
→ REQ-AUTHZ-003
→ TEST-AUTHZ-011..017
→ EVENT-POLICY-001
→ DET-AUTHZ-004
→ RUNBOOK-ACCESS-002
```

목적은 문서 번호를 늘리는 것이 아니라 변경 뒤 누락된 test·event·response를 찾는 것입니다.

## 9. negative requirement

하지 말아야 할 일도 구체적으로 적습니다.

- user input을 shell command string으로 조합하지 않습니다.
- production release는 mutable tag만으로 식별하지 않습니다.
- application process는 container runtime socket에 접근하지 않습니다.
- audit event에 raw credential·session token을 기록하지 않습니다.
- backup delete 권한과 production write 권한을 같은 identity에 주지 않습니다.

negative requirement도 자동·수동 검사 방법을 연결합니다.

## 10. exception과 residual risk

requirement를 즉시 만족하지 못하면 exception에 다음을 포함합니다.

```text
해당 requirement
미충족 이유
현재 exposure
compensating control
risk owner
risk acceptance authority와 승인 근거
만료일
monitoring
remediation milestone
re-review trigger
```

영구 exception이 되지 않도록 만료와 owner를 두고, 기술 reviewer·risk owner와 조직이 지정한 risk acceptance authority를 구분합니다.

## 11. requirement review

다음 변화에서 requirement를 다시 검토합니다.

- threat model·asset classification 변경
- 새 role·tenant·service·provider
- authorization·identity model 변경
- deployment·build·dependency source 변경
- incident와 새로운 attack pattern
- control owner 변경
- test·log가 더 이상 evidence를 제공하지 않음

## 12. 인접 소유권 경계

이 장은 보안 threat를 invariant·control·evidence로 바꾸는 방법을 소유합니다. 공개 서비스의
DNS·TLS·배포·backup 운영 자체는 `web-infra`, 여러 팀이 쓰는 golden path와 공통 policy·telemetry
플랫폼은 `platform-engineering`의 정본을 사용합니다. 이 브랜치에서는 그 결과물이 attack
path를 실제로 끊는지와 필요한 evidence를 제공하는지만 검토합니다.

법무·privacy·규제·감사 절차와 조직의 공식 risk acceptance 체계는 이 브랜치가 대신 만들지
않습니다. 조직의 GRC·법무 담당자가 정한 authority와 절차를 requirement의 외부 제약으로
연결합니다.

## 13. 이 장의 산출물

[보안 요구사항 template](../reference/security-requirement-template.md)을 사용해 threat 5개를 다음으로 변환합니다.

1. invariant
2. prevention requirement
3. detection requirement
4. recovery requirement
5. owner
6. normal·boundary·failure test
7. runtime evidence
8. exception·re-review rule
9. attack-path별 applicable·N/A·unknown matrix와 판단 근거

## 14. 완료 질문

- threat와 requirement의 차이는 무엇입니까?
- fail-closed가 항상 정답이 아닌 이유는 무엇입니까?
- 최소 권한을 검증 가능하게 쓰려면 어떤 차원이 필요합니까?
- requirement와 event·runbook을 연결해야 하는 이유는 무엇입니까?
- exception이 영구적인 약한 기본값이 되지 않도록 무엇을 기록합니까?
- threat 수준 coverage와 attack-path 수준 coverage를 왜 구분해야 합니까?
- monitoring이 containment와 같은 의미가 아닌 이유는 무엇입니까?
