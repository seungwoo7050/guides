# GitOps controller 실습

Local cluster와 test repository를 사용해 desired revision, reconciliation, drift, prune와 suspend를 관찰합니다. Flux 또는 Argo CD 중 하나를 선택합니다.

## 목표

- Git commit과 live Ready 상태를 구분합니다.
- controller가 source fetch·render·apply·health 단계를 수행하는지 봅니다.
- 수동 drift를 자동으로 되돌리는 조건을 확인합니다.
- prune와 deletion guardrail을 검토합니다.
- controller pause와 emergency change의 종료 과정을 연습합니다.

## 안전 기준

- production repository와 cluster를 사용하지 않습니다.
- controller credential을 실습 namespace/cluster에 제한합니다.
- secret plaintext를 repository에 넣지 않습니다.
- prune 전에 resource 목록과 data 수명을 확인합니다.

## 기본 흐름

1. test repository에 namespace와 작은 workload desired state를 저장합니다.
2. controller가 commit revision을 관찰하고 apply하는지 확인합니다.
3. Git에서 image 또는 replica를 바꾸고 observed revision과 Ready 시간을 기록합니다.
4. cluster에서 live field를 직접 수정해 drift와 correction을 봅니다.
5. controller를 suspend한 뒤 긴급 변경을 적용합니다.
6. 같은 변경을 Git에 반영하거나 되돌리고 controller를 resume합니다.
7. test resource 하나를 Git에서 제거해 prune preview/결과를 확인합니다.
8. controller와 cluster를 cleanup합니다.

## 기록할 상태

- desired commit
- controller observed revision
- reconciliation condition
- live object generation
- drift event
- suspend/resume audit
- prune 대상과 실제 삭제
- cleanup 결과

## 실패 질문

- Git fetch가 실패했을 때 기존 workload는 어떻게 됩니까?
- Admission이 manifest를 거부하면 어느 condition과 owner를 보여야 합니까?
- Manual hotfix가 controller에 즉시 되돌아가지 않으려면 어떤 절차가 필요합니까?
- Repository의 잘못된 path 변경이 여러 cluster에 확산되지 않게 어떻게 제한합니까?
