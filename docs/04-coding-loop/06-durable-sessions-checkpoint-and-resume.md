# 지속 session, checkpoint와 resume

## 목표

수십 분 이상 걸리는 코딩 작업을 중단·crash·재시작 뒤 안전하게 재개합니다. 대화 기록을 불러오는 것과 실제 tool effect를 복원하는 것을 구분합니다.

## durable state

checkpoint에 최소한 다음을 저장합니다.

```text
session identity
TaskSpec revision
RepositorySnapshot
InstructionManifest
EnvironmentManifest
current phase
confirmed facts·hypotheses·plan
ContextManifest와 summary
WorkspaceChangeSet
pending action·approval
ToolReceiptLog와 effect ledger
check results
budget usage
runtime·model·tool·policy versions
```

secret 원문과 대형 log는 artifact store reference로 분리합니다.

## event log와 checkpoint

### Event log

모든 중요 transition을 append-only event로 기록합니다.

### Checkpoint

특정 event offset까지의 복원 가능한 snapshot입니다.

```text
events 1..820
→ checkpoint at 820
→ events 821..
```

checkpoint만 덮어쓰면 crash 직전 effect를 잃을 수 있고, event만 replay하면 시간이 오래 걸릴 수 있습니다.

## checkpoint 시점

- repository snapshot 완료
- task·instruction 확정
- plan revision 확정
- approval 요청 전·후
- patch apply 전·후
- command start·finish
- external effect receipt 저장 뒤
- user pause·cancel
- context compaction 뒤
- final verifier 전·후

특히 effect 수행과 receipt 기록 사이의 crash window를 고려합니다.

## operation identity

외부 효과에는 `operation_id`를 둡니다.

```text
PREPARED
→ STARTED
→ EFFECT_OBSERVED
→ RECEIPT_COMMITTED
```

재개 시 `STARTED`에서 멈췄다면 effect가 발생했는지 실제 workspace, Git, process, remote system을 조회합니다. 결과를 확인하지 않고 같은 operation을 다시 실행하지 않습니다.

## resume 절차

1. checkpoint integrity와 schema version을 검사합니다.
2. repository·worktree identity를 다시 확인합니다.
3. task·instruction·permission expiry를 확인합니다.
4. pending process가 살아 있는지 확인합니다.
5. workspace digest와 change set receipt를 비교합니다.
6. incomplete operation을 reconcile합니다.
7. stale context와 plan을 표시합니다.
8. model provider state를 복원하거나 context를 재구성합니다.
9. 사용자에게 재개 상태와 divergence를 보여 줍니다.
10. 안전한 phase에서 실행을 계속합니다.

## workspace divergence

resume 사이 사용자가 file을 바꿀 수 있습니다.

```text
동일함              그대로 재개
agent file만 다름     receipt와 비교해 crash 복구
사용자 file 변경      context refresh·patch conflict
HEAD 변경             rebase/new session/manual review
instruction 변경      현재 session 적용 여부 확인
```

자동 merge가 가능한 경우에도 final diff와 acceptance를 다시 검증합니다.

## version 호환

runtime update 뒤 오래된 checkpoint를 읽을 수 있어야 할지 정책을 정합니다.

- schema version
- tool version
- action protocol
- permission policy
- model adapter event
- compaction format

호환되지 않으면 migration tool이나 read-only export를 제공합니다. 조용히 field를 무시하지 않습니다.

## cancellation과 cleanup

cancelled session도 durable final state입니다.

- child process 종료
- temporary credential revoke
- pending approval invalidate
- port·container·mount cleanup
- partial patch rollback 여부
- artifact retention
- reason과 actor 기록

## 실패 조건

- transcript만 저장하고 workspace receipt를 저장하지 않습니다.
- effect 실행 후 checkpoint 전에 crash하면 같은 effect를 다시 수행합니다.
- resume가 다른 HEAD에서 자동 patch를 계속합니다.
- expired approval과 credential을 재사용합니다.
- runtime version이 바뀌어도 checkpoint를 무검증 deserialize합니다.
- cancel 뒤 session directory와 secret이 무기한 남습니다.

## 완료 조건

- edit 직후, command 실행 중, approval 뒤 crash를 각각 복구하는 절차가 있습니다.
- resume가 repository divergence와 stale context를 탐지합니다.
- operation ledger로 effect 중복을 막습니다.
- checkpoint schema migration과 unsupported version 처리를 정의합니다.
