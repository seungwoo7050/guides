# 07. 로컬 Cloud 상태 모델

실제 cloud 계정 없이도 multi-tenant application의 상태 전이, 격리, quota, event 처리와 삭제 불변식을 반복해서 관찰하는 결정적 Python 모델입니다. provider emulator나 production SDK 연습이 아니라, 앞 단원에서 작성한 설계 판단을 실행 가능한 공개 행동으로 바꾸는 단원입니다.

## 완료 결과

학습자는 다음을 공개 API와 evidence로 입증합니다.

- stateful resource가 tenant별로 분리되고 public exposure가 없는지 판단합니다.
- 문서 소유권과 active document capacity quota를 모든 상태 전이 전에 검사합니다.
- event identity를 `(tenant_id, event_id)`로 정의하고 duplicate, payload conflict와 cross-tenant collision을 구분합니다.
- 정상 event마다 고유 output을 만들고, duplicate는 output과 usage를 한 번만 반영합니다.
- 실패 event의 attempt를 보존하고 정해진 경계에서 dead-letter로 종결합니다.
- tenant 삭제 시 active document, output, queue, dead letter, event 처리 상태와 resource를 지우되 tombstone과 aggregate usage evidence만 유지합니다.
- content를 노출하거나 내부 상태를 alias하지 않는 결정적 `evidence_snapshot(tenant_id)`를 제출합니다.

## 상태와 공개 계약

`CloudModel`은 `ACTIVE → DELETED`의 단방향 tenant lifecycle을 가집니다. 삭제한 tenant ID는 재사용할 수 없습니다. `starter`의 quota 2는 누적 write 횟수가 아니라 **동시에 존재하는 active document 수**입니다. 따라서 capacity에 도달해도 소유자가 기존 문서를 update할 수 있지만 새 문서는 원자적으로 거부되어야 합니다.

event registry의 identity는 tenant 범위입니다. 같은 tenant의 동일 ID와 동일 document 재전송은 허용하되 한 번만 효과를 냅니다. 동일 ID의 document가 바뀌면 `EventConflict`이며 queue를 바꾸지 않습니다. 서로 다른 tenant는 같은 event ID를 독립적으로 쓸 수 있습니다. 정상 event의 output ID에는 tenant, document와 event identity가 모두 반영되어 서로 다른 정상 event가 서로를 덮어쓰지 않아야 합니다.

구현이 제공해야 하는 공개 표면은 다음과 같습니다.

```python
CloudModel()
provision_tenant(tenant_id, plan="starter")
store_document(tenant_id, document_id, content)
read_document(requester_tenant, document_id)
enqueue_event(event_id, tenant_id, document_id)
process_next(max_attempts=2)
drain_events(max_attempts=2, max_steps=100)
usage_for(tenant_id)
delete_tenant(tenant_id)
resource_inventory()
evidence_snapshot(tenant_id)
```

공개 예외는 `CloudModelError`, `AccessDenied`, `QuotaExceeded`, `TenantInactive`, `EventConflict`입니다. validator는 내부 dict나 list 이름을 계약으로 삼지 않고 위 API와 `evidence_snapshot`만 관찰합니다.

## 안전한 시작

tracked skeleton을 직접 수정하지 말고 repository가 허용하는 learner workspace를 만듭니다.

```sh
./scripts/new_workspace.sh exercises/07-local-cloud-model
python3 scripts/verify_cloud_model.py \
  --implementation .workspace/07-local-cloud-model/cloud_model.py
```

starter가 아래의 알려진 8개 실패를 보이면 검증기가 제대로 실행된 것입니다. 구현을 보정한 뒤 같은 명령이 13개 check를 모두 통과해야 합니다. workspace wrapper로 같은 검사를 실행할 수도 있습니다.

```sh
./scripts/check_workspace.sh exercises/07-local-cloud-model
```

비교 구현은 학습자 workspace에 복사되지 않습니다. 막혔을 때 먼저 check의 관찰값과 이 문서의 상태 계약을 비교하고, 마지막에 [`reference/cloud_model.py`](reference/cloud_model.py)를 해설용으로 읽으십시오.

## 구현 순서와 대표 실패

1. tenant provisioning과 private resource inventory를 만듭니다. invalid plan, active duplicate와 deleted ID reuse가 상태를 바꾸지 않게 합니다.
2. owner read/write와 active document capacity를 구현합니다. foreign·missing read, foreign overwrite와 quota 초과가 partial state를 남기지 않게 합니다.
3. tenant-scoped event registry와 고유 output을 구현합니다. duplicate delivery, changed payload와 cross-tenant event/document mismatch를 각각 관찰합니다.
4. bounded retry와 dead letter를 구현합니다. `max_attempts=1`, exact retry boundary, invalid limit와 `max_steps` 초과의 공개 결과를 확인합니다.
5. tenant 삭제를 모든 active subsystem에 전파합니다. 다른 tenant는 유지하고 삭제 ID에는 late read/event/provisioning을 거부합니다.
6. content-free evidence를 반환합니다. 반환값을 변경해도 모델 상태가 변하지 않고 동일 상태에서 직렬화 결과가 같아야 합니다.

## 공개 check와 기대 evidence

| ID | 경로 | 판단하는 공개 행동 |
|---|---|---|
| `CM-001` | 정상·안전 | tenant의 두 stateful resource가 고유하고 private인가 |
| `CM-002` | 경계 | invalid plan과 잘못된 provisioning 전이가 원자적으로 거부되는가 |
| `CM-003` | 정상·경계 | capacity에서 owner update가 가능하고 active count가 유지되는가 |
| `CM-004` | 실패·격리 | foreign·missing read가 거부되고 보호 상태가 불변인가 |
| `CM-005` | 경계·실패 | active document quota 초과가 partial write 없이 거부되는가 |
| `CM-006` | 정상·재전송 | duplicate는 한 번만 반영되고 distinct event output은 구분되는가 |
| `CM-007` | 경계 | event ID가 tenant별로 독립이고 동일 tenant payload 변경은 충돌인가 |
| `CM-008` | 실패·경계 | retry attempt와 dead-letter 경계가 정확한가 |
| `CM-009` | 실패·격리 | foreign document event가 output/usage 없이 dead-letter되는가 |
| `CM-010` | 실패·안전 | bounded drain이 남은 작업을 숨기지 않고 evidence를 보존하는가 |
| `CM-011` | 정리 | 삭제가 active state 전체를 지우고 tombstone·usage만 남기는가 |
| `CM-012` | lifecycle | 반복 삭제가 멱등이고 삭제 tenant ID가 terminal인가 |
| `CM-013` | evidence | snapshot이 결정적·content-free·deep copy인가 |

starter의 예상 실패 ID는 `CM-001`, `CM-004`, `CM-005`, `CM-006`, `CM-007`, `CM-009`, `CM-010`, `CM-011`이며 [`contract.json`](contract.json)에 machine-readable하게 고정되어 있습니다. 다른 ID가 error이거나 이 목록이 달라지면 구현을 고치기 전에 import/API와 검증 환경부터 확인하십시오.

## 결정적 report 남기기

`--report`는 기존 evidence를 덮어쓰지 않으며 **새 파일만** 만듭니다. 같은 implementation과 contract에는 동일한 JSON이 생성됩니다.

```sh
report_dir="$(mktemp -d)"
python3 scripts/verify_cloud_model.py \
  --implementation .workspace/07-local-cloud-model/cloud_model.py \
  --report "$report_dir/cloud-model-report.json"
python3 -m json.tool "$report_dir/cloud-model-report.json"
rm "$report_dir/cloud-model-report.json"
rmdir "$report_dir"
```

report에는 implementation/contract SHA-256, stable check ID, 상태, content-free 관찰값과 evidence hash, 실행 제약이 들어갑니다. missing path, import failure와 public API 누락은 contract fail과 구분된 `E_PATH`, `E_IMPORT`, `E_API` 오류 및 exit code 2로 보고됩니다. 기존 report 경로도 `E_REPORT`로 거부됩니다.

## 사람 검토와 한계

자동 검사는 이 합성 모델의 공개 행동만 판단합니다. 다음 질문은 코드와 report를 함께 보고 사람이 확인하십시오.

1. 각 mutation 전에 authorization과 quota를 검사하여 concurrent/transactional 구현으로 옮길 수 있는 명시적 invariant가 있는가?
2. tenant, document, event와 output identity의 범위가 설계 문서와 일치하는가?
3. 삭제 후 보존하는 tombstone·usage evidence의 목적과 retention 기간을 실제 정책에 기록했는가?
4. dead letter의 운영 owner, replay 조건, poison event 격리와 alert가 별도 운영 계획에 있는가?
5. 실제 provider에서 IAM, network exposure, backup, key, log, cache와 billing까지 integration test하는가?

이 validator는 실제 IAM·network·queue·billing·physical deletion, distributed transaction, process crash, concurrent writer를 검증하지 않습니다. learner Python은 5초 제한의 child process에서 실행되지만 현재 사용자 권한을 그대로 사용하며 OS sandbox가 아니므로 신뢰할 수 없는 코드를 실행하지 마십시오. 외부 cloud resource를 만들지 않으며 network도 필요하지 않습니다.
