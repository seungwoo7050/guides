# GitOps reconciliation과 긴급 변경

GitOps는 deployment YAML을 Git repository에 저장하는 것만으로 성립하지 않습니다. Versioned desired state, 자동 reconciliation, 명시적인 drift 처리와 pull-based 변경 경계가 함께 있어야 합니다.

이 장은 [`03 Control plane과 reconciliation`](03-control-planes-and-reconciliation.md)의 일반 제어 루프를 delivery 환경에 적용합니다.

## 1. Git이 소유하는 것

Git repository는 다음을 소유할 수 있습니다.

- 환경별 desired release digest
- versioned configuration
- policy와 platform profile reference
- namespace·workload·route 같은 선언
- promotion과 승인 기록을 연결하는 변경 이력

Git이 소유하지 않는 것:

- 현재 Pod의 실제 상태
- controller의 retry queue
- 외부 cloud resource의 모든 live field
- secret plaintext
- telemetry backend의 관측 결과
- application data

Git commit은 desired state를 증명하지만 실행 완료를 증명하지 않습니다.

## 2. Repository layout과 소유권

Layout에는 하나의 정답이 없지만 writer와 blast radius를 명확히 해야 합니다.

가능한 형태:

```text
environments/
  staging/
    checkout/
  production/
    checkout/
```

또는 team/service별 repository를 사용할 수 있습니다.

검토 항목:

- 누가 어느 path에 write할 수 있습니까?
- 한 pull request가 몇 environment와 service를 바꿉니까?
- common base 변경의 fan-out은 얼마입니까?
- promotion이 copy인지 version reference 변경인지 명확합니까?
- controller가 감시하는 path와 cluster가 일대일로 추적됩니까?
- repository 손상 또는 접근 상실 시 복구할 수 있습니까?

예시 layout은 [`examples/gitops/repository-layout.txt`](../examples/gitops/repository-layout.txt)에 있습니다.

## 3. Reconciliation 결과

GitOps controller는 단순 apply command가 아닙니다.

```text
Git desired revision 읽기
→ source 인증과 parse
→ render 또는 compose
→ policy·validation
→ live state 비교
→ create/update/delete
→ health 평가
→ status와 event 기록
```

각 단계의 실패를 구분합니다.

- source fetch 실패
- signature 또는 authorization 실패
- invalid manifest
- render dependency 실패
- admission 거부
- API timeout
- apply conflict
- health timeout
- prune 차단

“sync failed” 하나로 뭉치면 사용자가 행동할 수 없습니다.

## 4. Drift

Drift 원인:

- 사람이 cluster에서 직접 수정
- 다른 controller가 같은 field 수정
- admission mutation
- runtime이 default field 추가
- external operator가 resource 변경
- Git desired state가 stale

처리 정책:

| Drift 종류 | 행동 |
|---|---|
| 예상된 runtime field | 비교에서 무시하거나 별도 owner 지정 |
| admission이 채운 default | rendered desired state에 반영하거나 정상화 |
| 허용되지 않은 수동 변경 | 자동 revert와 audit |
| 긴급 임시 변경 | break-glass workflow로 Git에 후속 반영 |
| controller ownership 충돌 | reconciliation 중단, field owner 수정 |
| 실제 desired state 오류 | Git change와 rollback |

Controller를 강하게 설정하기 전에 어떤 field를 누가 관리하는지 명확히 합니다.

## 5. Prune와 삭제

Git에서 파일을 지우면 live resource를 지우는 설정은 강력합니다.

삭제 전 확인:

- resource가 stateful입니까?
- finalizer 또는 backup이 필요합니까?
- 다른 service가 참조합니까?
- namespace·cluster 단위 cascade가 발생합니까?
- rename이 delete/create로 해석됩니까?
- 잘못된 branch/path 선택이 대량 삭제를 만들 수 있습니까?

Production에는 다음 guardrail을 사용할 수 있습니다.

- prune preview
- protected resource annotation
- environment별 승인
- deletion budget
- namespace 또는 resource allowlist
- controller pause
- backup·retention condition

삭제를 영구 금지하면 orphan가 쌓입니다. 대신 위험에 맞는 조건을 둡니다.

## 6. Promotion과 Git commit

Delivery system이 production desired state를 변경할 때 누구의 identity로 commit하는지 정합니다.

- 사람 PR
- promotion bot PR
- verified artifact record에서 자동 commit
- API가 Git writer를 통해 commit

Commit에는 다음을 연결합니다.

- source artifact digest
- 이전 environment evidence
- policy decision
- requester와 approver
- rollout strategy
- rollback target

Generated manifest 전체를 사람이 리뷰하는 대신 의미 있는 diff와 evidence를 보여 줄 수 있어야 합니다.

## 7. 긴급 변경과 break-glass

사고 중에는 Git 경로가 너무 느리거나 controller 자체가 문제일 수 있습니다. 직접 변경을 무조건 금지하기보다 통제된 break-glass 절차를 둡니다.

```text
사고와 영향 확인
→ break-glass identity 발급
→ 범위·시간·승인 기록
→ 최소 가역 변경 실행
→ audit와 before/after evidence 보존
→ controller 충돌 방지 또는 일시 중지
→ Git desired state에 반영
→ reconciliation 재개
→ 임시 credential 폐기
→ 후속 검토
```

중요한 계약:

- 누가 사용할 수 있는가?
- 어떤 resource와 verb만 허용하는가?
- credential은 얼마나 짧게 유효한가?
- controller가 즉시 되돌리지 않도록 어떻게 조정하는가?
- live change를 Git에 언제 반영하거나 제거하는가?
- 종료 여부를 누가 확인하는가?

“사고라서 기록하지 못했다”는 허용하지 않습니다. 자동 audit를 최소 경계로 둡니다.

## 8. Controller outage

GitOps controller가 중단돼도 기존 workload는 계속 실행될 수 있습니다. 그러나 다음 기능은 멈춥니다.

- 새 deployment
- drift correction
- policy 또는 config update
- secret reference 갱신
- 삭제와 cleanup

Runbook은 다음을 구분합니다.

- controller 자체 장애
- source repository 장애
- API server 장애
- credential 만료
- queue backlog
- 특정 resource의 reconcile loop

긴급하게 manual apply를 허용할지, controller 복구를 먼저 할지 사용자 영향과 변경 risk로 결정합니다.

## 9. Multi-cluster와 ordering

여러 cluster를 하나의 변경으로 갱신할 때 부분 성공을 정상 상태로 모델링합니다.

```text
cluster-a Ready
cluster-b HealthTimeout
cluster-c SourceFetchFailed
```

전체를 `Failed`로만 기록하지 않습니다. 다음을 정합니다.

- wave와 dependency
- 최대 동시 변경 수
- region 또는 tenant별 canary
- 중단 조건
- 이미 성공한 cluster의 rollback 여부
- 뒤늦게 복구된 controller가 stale change를 적용하지 않는 조건

Git commit 순서만으로 runtime 완료 순서를 보장하지 않습니다.

## 10. GitOps security boundary

- Repository write 권한은 deployment 권한입니다.
- Controller credential은 최소 cluster·namespace·verb로 제한합니다.
- Source와 artifact signature를 확인할 수 있습니다.
- Pull request review가 모든 runtime policy를 대체하지 않습니다.
- Secret plaintext를 Git에 저장하지 않습니다.
- Generated configuration의 source와 generator version을 추적합니다.
- Dependency가 원격 URL을 임의로 가져오지 않게 pinning과 allowlist를 둡니다.

정책과 supply chain은 [`16 Supply chain과 platform security`](16-supply-chain-and-platform-security.md)에서 확장합니다.

## 11. 관측 근거

필요한 신호:

- desired revision과 observed revision
- source fetch latency/error
- reconcile duration과 queue depth
- resource별 apply·prune 결과
- health timeout
- drift 감지와 자동 revert
- suspended controller와 이유
- break-glass event
- cluster별 wave 진행 상태

Alert는 controller error 하나보다 사용자 여정에 미치는 영향을 연결합니다. 예를 들어 staging controller 지연과 production 변경 불가를 다른 심각도로 다룰 수 있습니다.

## 12. 실습

[`07-delivery-gitops`](../exercises/07-delivery-gitops/)에서 다음을 설계합니다.

- Git desired state와 live state의 소유권
- repository path와 writer
- promotion commit evidence
- drift 종류별 처리
- prune guardrail
- controller outage와 multi-cluster 부분 성공
- break-glass 시작·종료 계약

## 13. 검토 질문

- Git이 소유하는 field와 live controller가 소유하는 field가 구분됩니까?
- Desired revision과 실제 Ready revision을 각각 조회할 수 있습니까?
- Manual drift가 자동으로 되돌아가도 안전합니까?
- Prune가 stateful resource와 rename을 잘못 삭제하지 않습니까?
- Break-glass가 제한된 identity·시간·범위·audit를 가집니까?
- Controller outage 중 가능한 행동과 금지할 행동이 명확합니까?
- 여러 cluster의 부분 성공을 독립적으로 추적합니까?

다음 장에서는 전달 경로를 실행하는 사람·workload·automation의 identity, secret과 policy 적용 지점을 설계합니다.
