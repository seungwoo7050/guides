# 사고 대응과 복구

incident response는 침해가 확인된 뒤 시작하는 별도 절차가 아닙니다. 준비·탐지·대응·복구 능력은 threat model, logging, identity, release와 backup 설계에 미리 포함돼야 합니다.

NIST SP 800-61 Rev. 3은 incident response를 NIST CSF 2.0의 전체 risk-management 활동에 통합합니다. 이 장도 사건 전과 후를 하나의 수명 주기로 다룹니다.

## 1. incident와 finding

- vulnerability finding: 악용 가능한 보안 실패가 존재함
- suspicious event: 설명이 필요한 비정상 신호
- incident: 실제 또는 임박한 policy·security impact가 대응을 요구함

confirmed vulnerability가 있어도 exploitation evidence가 없을 수 있고, 알려진 vulnerability 없이 stolen credential incident가 발생할 수도 있습니다.

## 2. 준비

사건 전에 다음이 있어야 합니다.

- incident severity와 escalation 기준
- incident commander와 역할
- 연락 경로와 대체 channel
- asset·identity·data owner
- log·snapshot·backup 접근
- credential revoke·rotate 절차
- traffic·feature·deployment containment 방법
- trusted rebuild source
- 사용자·고객·법무·provider communication 경계
- tabletop·restore drill

runbook이 존재해도 credential과 권한이 실제로 작동하는지 정기적으로 확인합니다.

## 3. 사실·가설·결정 log

incident timeline에 다음 type을 구분합니다.

```text
FACT       직접 확인한 event·state
HYPOTHESIS 사실을 설명하는 미확인 원인
DECISION   누가 어떤 근거로 선택한 조치
ACTION     실제 수행한 변경
RESULT     action 뒤 관찰한 상태
UNKNOWN    현재 확인할 수 없는 범위
```

예:

```text
FACT 01:02 user-17이 foreign report-82 read에서 200을 받음
HYPOTHESIS object authorization 누락
DECISION 01:10 report download를 authenticated owner-only mode로 제한
ACTION 01:12 feature flag 변경
RESULT 01:14 synthetic cross-owner request가 403, owner request는 200
```

## 4. evidence preservation

- 원본 log·artifact·snapshot을 read-only copy로 보존
- source·timestamp·hash·collector 기록
- 조사 대상 host에서 불필요한 cleanup 금지
- timezone·clock skew 기록
- volatile evidence가 필요한지 판단
- 실제 secret·personal data 접근 제한
- evidence copy와 working note 분리

법적·규제·노동 문제의 전문 절차는 조직의 담당자에게 escalation합니다.

backup과 incident evidence는 목적이 다릅니다. backup은 서비스 상태를 복원하기 위한 copy이고
retention·deduplication·restore 과정에서 metadata가 바뀔 수 있습니다. evidence는 사실을
재구성할 수 있도록 원본성, 수집 주체·방법, 시간, hash와 취급 이력을 보존해야 합니다.
backup이 둘 다의 역할을 할 수는 있지만 자동으로 forensic evidence가 되지는 않습니다.
containment나 cleanup이 log rotation·snapshot·backup을 덮어쓸 수 있으면 안전을 지연하지 않는
범위에서 먼저 보존하거나 별도 evidence hold를 적용합니다. hash 일치도 copy가 바뀌지 않았다는
근거이지 source event가 참이었다는 증명은 아닙니다.

## 5. containment

목표는 확산과 추가 영향을 줄이는 것입니다.

### 선택 예

- token·session revoke
- privileged identity 사용 중단
- endpoint·feature 제한
- egress·storage scope 축소
- compromised artifact 배포 중단
- affected host·workload 격리
- write path를 read-only 또는 queue 보류로 전환

각 조치의 부작용을 기록합니다.

- evidence 손실
- 사용자 가용성
- 자동 retry로 인한 추가 부하
- attacker가 행동을 바꿀 가능성
- rollback과 복구 난이도

추가 logging, alert threshold 조정, account monitoring은 containment 효과를 관찰하고 새로운
시도를 찾는 detection action입니다. token revoke, isolation, write 차단처럼 capability나
attack-path edge를 실제로 제거하지 않으므로 containment 완료로 세지 않습니다. 반대로
containment도 이미 일어난 영향의 eradication이나 recovery를 자동 완료하지 않습니다.

## 6. eradication

단순 process kill이나 file 삭제가 아닙니다.

- initial access와 root cause 수정
- compromised identity·key·session 폐기
- persistence·scheduled job·modified policy 조사
- malicious·unknown artifact 제거
- vulnerable dependency·configuration 교체
- affected data·derived state 확인
- 같은 trust path의 다른 environment 조사

확인하지 못한 영역을 clean으로 선언하지 않습니다.

## 7. recovery

신뢰할 수 있는 source에서 상태를 재구성합니다.

```text
clean source revision
+ trusted builder
+ verified artifact digest
+ rotated credential
+ validated configuration
+ integrity-checked data·backup
+ active telemetry
```

먼저 **recovery trust anchor**를 명시합니다. 이는 compromised boundary 밖에서 독립적으로
검증할 수 있는 source revision·key·builder identity·보존된 configuration baseline·
compromise 이전 backup 같은 기대 상태의 기준입니다. 다음 질문에 답하지 못하면 “clean
rebuild”라고 선언하지 않습니다.

- source repository나 CI가 영향 범위라면 어떤 독립 copy와 review로 source를 신뢰합니까?
- signing key나 builder가 영향 범위라면 기존 signature·provenance를 왜 계속 믿을 수 있습니까?
- dependency·base image·build parameter를 어떤 allowlist와 digest로 고정합니까?
- restore backup이 compromise 이전 상태이며 필요한 integrity를 가진다는 근거는 무엇입니까?
- 새 credential과 configuration이 이전 trust path를 재사용하지 않는다는 근거는 무엇입니까?

signature는 특정 key가 digest에 서명했다는 근거이고 provenance는 주장된 build 관계의
attestation입니다. compromised signer·builder가 만든 artifact까지 clean하다고 증명하지
않습니다. 따라서 source, builder, key, dependency, data backup 가운데 손상 가능성이 있는
층을 trust anchor 밖의 근거로 다시 세웁니다.

복구 검증:

- 정상 사용자 경로
- security regression
- old credential·artifact deny
- logging·alert health
- data integrity·reconciliation
- performance·capacity
- external smoke
- monitoring period와 exit criteria

recovery validation은 정상 동작과 알려진 공격의 거부를 관찰할 뿐 모든 persistence가
제거됐음을 증명하지 않습니다. 확인하지 못한 identity·asset·time 범위를 `UNKNOWN`으로 남기고
monitoring period가 끝날 조건과 재개할 incident trigger를 둡니다.

## 8. scope와 blast radius

다음 축으로 조사합니다.

- time: 최초 가능 시점부터 containment까지
- identity: user·service·CI·admin·key
- asset: host·service·tenant·bucket·repository
- data: read·write·delete 가능 범위
- release: affected artifact·environment
- evidence: log·backup·audit 신뢰성

“한 endpoint에서 발견”과 “그 endpoint만 영향”을 동일시하지 않습니다.

## 9. communication

기술 timeline과 communication timeline을 함께 관리합니다.

- 내부 의사결정자
- 서비스 owner·support
- 사용자·고객
- provider·maintainer
- 법무·privacy·regulatory 담당
- 외부 researcher

확인된 사실, 현재 영향, 조치, 다음 update 시간을 구분합니다. 추측을 사실처럼 전달하지 않습니다.

## 10. post-incident review

개인을 비난하는 대신 control과 system 조건을 분석합니다.

- 어떤 assumption이 틀렸는가?
- prevention이 왜 실패했는가?
- detection이 왜 늦거나 불완전했는가?
- response에 필요한 권한·문서·evidence가 있었는가?
- recovery source를 신뢰할 수 있었는가?
- 같은 class를 다른 곳에서 어떻게 찾을 것인가?

follow-up에는 owner·priority·deadline·verification을 둡니다.

## 11. exercise와 drill

### Tabletop

상태와 의사결정을 토론합니다. 실제 control 동작을 증명하지 않습니다.

### Functional drill

credential revoke, feature isolation, restore, alert routing 같은 한 기능을 실행합니다.

### Full simulation

격리 환경에서 detection부터 recovery까지 종단 간 수행합니다.

production에 무단 공격 traffic을 만들지 않습니다. synthetic identity·data와 승인된 시간 창을 사용합니다.

실제 backup·배포·관측 파이프라인의 구축과 일상 운영은 `web-infra`, 여러 팀용 공통 복구·
telemetry 경로는 `platform-engineering`의 소유 범위를 사용합니다. 이 브랜치의 책임은 incident
가설에서 어떤 trust anchor·containment·recovery evidence가 필요한지 정하고 격리된 공격
경로에서 검증하는 것입니다. 법적 보존·통지·공식 risk 결정은 조직의 GRC·법무 절차에
escalation합니다.

## 12. 이 장의 산출물

[사고 timeline 실습](../exercises/06-incident-timeline/README.md)에서 다음을 작성합니다.

1. severity와 incident declaration 근거
2. fact·hypothesis·decision timeline
3. affected identity·asset·time scope
4. evidence preservation plan
5. containment options와 trade-off
6. eradication checklist
7. trusted recovery plan
8. communication update
9. post-incident follow-up
10. backup과 incident evidence의 구분·보존 근거
11. recovery trust anchor와 아직 신뢰하지 못하는 범위

## 13. 완료 질문

- vulnerability와 incident는 어떻게 다릅니까?
- containment가 evidence와 가용성에 줄 수 있는 부작용은 무엇입니까?
- process를 종료했다고 eradication이 끝난 것이 아닌 이유는 무엇입니까?
- 복구 artifact와 backup을 왜 다시 신뢰 검증해야 합니까?
- tabletop과 functional drill은 각각 무엇을 증명하지 못합니까?
- monitoring이 containment나 eradication을 대신하지 못하는 이유는 무엇입니까?
- compromised builder의 서명된 artifact가 recovery trust anchor가 될 수 없는 이유는 무엇입니까?
