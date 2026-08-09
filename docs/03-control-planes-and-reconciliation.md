# Control plane과 reconciliation

## 1. 비동기 작업을 상태 기계로 봅니다

환경 생성은 한 번의 함수 호출로 끝나지 않습니다.

```text
요청 저장
→ account 또는 project 확인
→ network·identity 준비
→ namespace와 policy 생성
→ desired-state repository 갱신
→ GitOps controller 적용
→ workload readiness 확인
→ external smoke 확인
→ Ready 보고
```

중간에 process가 종료되거나 API가 timeout돼도 같은 요청을 다시 처리할 수 있어야 합니다. 이를 위해 “단계를 순서대로 실행하는 script”보다 desired state와 observed state를 반복 비교하는 control loop가 필요합니다.

Kubernetes controller pattern과 공식 API 개념은 [source index의 control loop](../reference/source-index.md#control-loop)를 확인하세요.

## 2. Desired state와 actual state를 구분합니다

### Desired state

사용자가 원하는 결과입니다.

```json
{
  "service": "checkout",
  "environment": "staging",
  "runtimeProfile": "kubernetes-standard@3.4",
  "artifactDigest": "sha256:..."
}
```

### Observed state

controller가 dependency에서 실제로 확인한 상태입니다.

```text
namespace exists
workload identity issued
GitOps revision applied
Deployment available replicas = desired replicas
external smoke passed
```

### Status

control plane이 observed state를 해석해 사용자에게 보고한 결과입니다.

```text
Ready=False
Reason=WorkloadNotReady
ObservedGeneration=7
Evidence=deployment/checkout condition Available=False
```

status는 희망이나 마지막 명령의 성공이 아니라 관측 근거를 요약해야 합니다.

## 3. Generation과 observed generation을 사용합니다

사용자가 spec을 변경하면 generation이 증가합니다. controller는 어떤 generation을 처리했는지 status에 기록합니다.

이 구분이 없으면 이전 spec에 대한 `Ready=True`가 새 요청에도 유효해 보일 수 있습니다.

```text
metadata.generation = 8
status.observedGeneration = 7
status.Ready = True
```

위 상태는 최신 요청이 완료된 것이 아닙니다. UI와 automation은 generation이 일치하는지 확인해야 합니다.

## 4. Condition은 단계가 아니라 의미를 표현합니다

단일 phase만 사용하면 동시에 존재하는 상태를 잃습니다.

예:

- `Accepted`: 입력과 정책을 통과했습니다.
- `InfrastructureReady`: 기반 자원이 준비됐습니다.
- `DesiredStatePublished`: 배포 desired state가 생성됐습니다.
- `WorkloadReady`: runtime readiness를 통과했습니다.
- `Ready`: 사용자 관점의 완료 evidence를 충족했습니다.
- `Degraded`: 완료 상태였지만 현재 일부 보장이 깨졌습니다.

각 condition에는 최소한 다음이 필요합니다.

```text
type
status: True | False | Unknown
reason: 안정적인 기계 판독 값
message: 사람이 다음 행동을 이해할 설명
observedGeneration
lastTransitionTime
```

`Reconciling=True`와 `Ready=False`는 함께 존재할 수 있습니다.

## 5. Reconcile 함수는 반복 가능해야 합니다

좋은 reconcile은 다음 형태입니다.

```text
현재 desired state를 읽습니다.
→ dependency의 실제 상태를 관찰합니다.
→ 가장 작은 안전한 차이를 계산합니다.
→ 필요한 한 가지 변경을 수행합니다.
→ status와 다음 재시도 조건을 기록합니다.
```

재실행해도 같은 외부 효과가 중복되지 않아야 합니다.

- 자원 이름과 identity를 안정적으로 만듭니다.
- create 전에 관찰하고, create 결과가 불확실하면 다시 관찰합니다.
- 외부 요청에 idempotency key를 사용합니다.
- 긴 작업은 operation ID를 저장합니다.
- 성공 여부를 응답 하나가 아니라 실제 상태에서 확인합니다.

이 원리는 `distributed-services`의 idempotency와 uncertain outcome에 연결됩니다. 여기서는 platform resource의 제어 상태에 적용합니다.

## 6. 오류를 세 종류로 나눕니다

### Transient

자동 재시도가 의미 있습니다.

- provider API 일시 timeout
- repository 일시 접근 실패
- rate limit
- dependency가 아직 준비 중

status에 다음 retry 시점과 마지막 evidence를 남깁니다. 무제한 빠른 retry로 dependency를 압박하지 않습니다.

### Terminal for current spec

같은 입력으로 재시도해도 해결되지 않습니다.

- 존재하지 않는 runtime profile
- 허용되지 않은 region
- policy 위반
- 이름 충돌

`Ready=False`, 안정적인 reason과 사용자가 수정할 field를 제공합니다. spec이 바뀔 때 다시 처리합니다.

### Operator action required

자동 판단이 위험합니다.

- destructive IaC plan
- state identity 충돌
- partial deletion 뒤 orphan resource
- 정책 bundle 자체의 오류

자동 retry를 멈추고 owner, runbook과 audit context를 연결합니다.

## 7. Finalizer와 삭제 계약

사용자가 platform resource를 삭제했다고 외부 cloud resource가 자동으로 사라지는 것은 아닙니다.

삭제 흐름:

```text
deletion timestamp 관찰
→ 신규 변경 차단
→ workload traffic·job 종료
→ dependent desired state 제거
→ external resource 정리
→ retention 대상 분리
→ cleanup evidence 기록
→ finalizer 제거
```

finalizer가 영구히 남는 실패도 설계해야 합니다.

- 어떤 단계에서 멈췄습니까?
- 재시도해도 안전합니까?
- 강제 제거가 orphan 또는 data loss를 만들 수 있습니까?
- manual recovery 뒤 어떤 상태를 정본에 반영합니까?

## 8. 여러 controller의 소유 field를 분리합니다

같은 object를 여러 controller가 수정할 수 있지만 같은 field를 경쟁적으로 쓰면 안 됩니다.

예:

```text
platform API controller
- spec validation
- high-level conditions

environment controller
- cloud·namespace outputs

release controller
- artifact와 rollout conditions

policy controller
- compliance condition
```

각 controller의 writer scope와 dependency를 명시합니다. status aggregation controller가 다른 condition을 덮어쓰지 않게 합니다.

## 9. Reconciliation의 안전성과 진행

### Safety

절대 발생하면 안 되는 상태입니다.

- 두 tenant가 같은 identity 또는 namespace를 공유합니다.
- production에서 승인되지 않은 artifact가 실행됩니다.
- deletion 중 retention 대상 데이터가 제거됩니다.
- stale generation의 성공 status가 최신 요청으로 노출됩니다.

### Liveness

조건이 충족되면 언젠가 진행해야 하는 상태입니다.

- transient dependency가 회복되면 reconcile이 다시 실행됩니다.
- 새 generation이 관찰됩니다.
- deletion cleanup이 성공하면 finalizer가 제거됩니다.
- controller restart 뒤 미완료 resource가 다시 처리됩니다.

실제 consensus와 replicated control plane 내부는 `distributed-systems`의 범위입니다. 이 가이드에서는 application-level controller가 기대하는 API 보장과 자신의 상태 기계를 검증합니다.

## 10. 관측과 debugging

하나의 reconcile마다 다음을 연결합니다.

- resource UID와 generation
- reconcile ID
- controller version
- 시작·종료·결과 reason
- 변경한 외부 resource identity
- retry count와 next retry
- dependency latency
- status transition

사용자 message에는 내부 stack trace를 노출하지 않지만, operator evidence와 연결되는 stable reason을 제공합니다.

## 11. 실습

[`03-reconciliation`](../exercises/03-reconciliation/)에서 platform resource의 spec·status·condition·transition·retry·finalizer·invariant를 설계합니다.

반드시 다음 실패를 포함합니다.

1. create 응답을 받기 전에 controller가 종료됩니다.
2. 이전 generation의 작업이 늦게 완료됩니다.
3. dependency가 일시적으로 실패합니다.
4. 사용자가 삭제를 요청했지만 외부 cleanup이 실패합니다.
5. operator 판단이 필요한 destructive change가 발견됩니다.
