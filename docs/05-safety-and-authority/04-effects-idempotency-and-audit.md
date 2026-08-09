# 외부 효과, 멱등성과 audit

## 목표

파일 변경, dependency 설치, process 시작, Git commit과 remote action이 중단·재시도 뒤 중복되지 않게 합니다. 모델이 요청한 의도와 실제 시스템 효과를 receipt로 연결합니다.

## coding agent의 effect

```text
파일 생성·수정·삭제
formatter·generator에 의한 추가 변경
package install과 lockfile 변화
background service와 port
Git index·branch·commit
cache·database·container
remote issue·PR·push
```

read-only로 보이는 command도 cache나 timestamp를 바꿀 수 있습니다. tool catalog에 expected mutation을 명시하고 실제 before/after를 측정합니다.

## operation identity

같은 업무 효과를 재시도할 때 동일한 `operation_id`를 사용합니다.

```text
operation_id = session 안의 논리적 effect
attempt_id   = effect를 수행하거나 확인한 개별 시도
```

같은 operation ID와 다른 arguments는 충돌로 거절합니다.

## effect ledger

```text
operation_id
operation_type
arguments_digest
resource_scope
state
attempts[]
prepared_artifact
approval_id
started_at
observed_receipt
committed_at
compensation?
```

상태 예시:

```text
PREPARED
→ AUTHORIZED
→ STARTED
→ APPLIED
→ VERIFIED
→ COMMITTED
```

오류:

```text
UNKNOWN
PARTIALLY_APPLIED
COMPENSATION_REQUIRED
CONFLICT
```

## 파일 effect

file patch는 before/after digest와 changed path를 receipt로 남깁니다. crash 뒤 ledger가 `STARTED`라면 실제 file digest를 확인해 이미 적용됐는지 판정합니다.

## process effect

background process는 PID만으로 identity를 정하지 않습니다.

- process group/job identity
- executable·argv digest
- cwd·env profile
- port·socket
- start time
- health evidence

resume 시 PID reuse를 고려하고 실제 process signature를 확인합니다.

## Git effect

commit은 tree와 parent identity로 확인할 수 있습니다. commit command의 응답을 잃어도 HEAD와 object를 조회해 결과를 확정합니다.

remote push는 더 복잡하므로 기본 Capstone에서 제외합니다. 확장 시 remote ref와 server receipt를 조회합니다.

## 보상과 rollback

모든 effect가 완전히 되돌아가지는 않습니다.

- file patch: inverse patch 또는 worktree 폐기
- dependency install: ephemeral environment 폐기
- process: terminate와 artifact cleanup
- commit: 새 revert 또는 branch 폐기
- remote message: 삭제 불가능할 수 있음

`rollback available`이라는 label보다 실제 절차와 잔여 상태를 기록합니다.

## audit log

감사 기록에는 다음이 필요합니다.

- 누가 task와 승인을 제공했는지
- 어떤 model request가 action을 제안했는지
- policy가 어떤 input으로 판정했는지
- 실제 tool arguments와 version
- effect receipt와 workspace 변화
- 사용자 revoke·cancel
- verifier 결과

secret과 source 원문을 무조건 모두 저장하지 않습니다. identity와 digest, 제한된 artifact access를 사용합니다.

## 실패 조건

- model retry가 file patch나 command를 새 operation으로 반복합니다.
- tool 성공 응답을 잃으면 실패로 가정하고 재실행합니다.
- audit에 model의 자연어 summary만 남습니다.
- 같은 operation ID에 다른 patch를 허용합니다.
- rollback이 실제 resource cleanup을 확인하지 않습니다.
- remote effect가 발생했는지 조회 경로가 없습니다.

## 완료 조건

- file·process·Git effect에 operation identity와 receipt가 있습니다.
- crash window에서 `UNKNOWN`을 판정하고 실제 상태를 조회합니다.
- 같은 effect가 resume 뒤 한 번만 남습니다.
- audit가 model proposal부터 verifier까지 연결됩니다.
