# Evidence and Failure Review

## 공통 식별자

검토 대상은 service `svc-payments`, resource `env-payments-staging`, operation `op-payments-staging-v3`, tenant `tenant-checkout`, artifact `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, profile `stateless-http/v3`다.

## 실패 시나리오

아래 8개 시나리오는 단순 경고 문구가 아니라 상태, 공개 결과, owner, cleanup/복구와 evidence가 있는지 검토한다. 파일·heading과 model JSON pointer는 `evidence-manifest.json`에 연결되어 있다.

### FS-01 — Idempotency payload conflict

같은 key와 같은 payload는 기존 operation을 반환한다. artifact/profile을 바꾼 payload는 `IDEMPOTENCY_CONFLICT`로 거부되고 새 environment, quota reservation 또는 provider effect가 없어야 한다. application owner가 새 key를 만들거나 기존 request를 유지하며 platform은 기존 operation ref를 제공한다.

### FS-02 — Evidence-free Ready와 partial effect

provider effect 뒤 smoke evidence가 없으면 `Ready`를 발행하지 않는다. `Degraded`와 created external ID, cleanup owner, retryability를 공개한다. provider object를 숨긴 채 성공/실패만 반환하는 상태는 허용하지 않는다.

### FS-03 — Tenant quota와 queue isolation

quota 2를 넘는 `tenant-checkout` request는 effect 없이 거부한다. 그 request의 backoff가 다른 tenant queue를 막지 않아야 한다. quota observation, zero-effect count와 다른 tenant 진행 상태가 evidence다.

### FS-04 — Drift와 bounded break-glass

일반 live drift는 desired artifact로 되돌리고 before/after를 남긴다. emergency change는 approver, reason, expiry와 evidence 중 하나라도 없으면 거부한다. 유효 exception도 만료 후 자동 수렴과 close evidence가 필요하다.

### FS-05 — Static credential fallback

workload identity issuer가 unavailable이면 operation은 `Blocked`가 된다. long-lived access key나 shared secret으로 자동 fallback하지 않는다. owner, retry 조건, issuer 상태와 static denial code를 공개한다.

### FS-06 — Migration wave abort

두 번째 wave가 threshold를 넘으면 그 wave는 `Failed`, 이후 wave는 `Pending`이고 migration은 `Aborted`다. 이미 바뀐 resource를 inventory하고 rollback 또는 승인된 roll-forward를 선택한다. 미실행 wave를 성공으로 기록하지 않는다.

### FS-07 — Downstream partial provisioning

network만 생성되고 runtime이 실패한 경우 provider ID, state serial, cost exposure, cleanup/converge owner가 operation에 남는다. retry는 동일 operation identity와 journal을 사용해 중복 생성하지 않는다.

### FS-08 — Service retirement cleanup

traffic, data decision, credential/exception, runtime/provider resource, queue/quota, catalog와 cost inventory가 닫혀야 `Retired`다. 다른 service는 보존되고 audit tombstone에는 secret material 없이 hash와 retention class만 남는다.

## Model Evidence

`evidence/platform-model-report.json`은 reference implementation을 5초 제한 child process에서 실행한 결정적 결과다. `PE-001..PE-010`이 모두 통과하며 canonical six ID, implementation, public `contract.json`, 실행되는 `tests/contract.py`와 report SHA-256을 manifest가 고정한다. capstone validator는 manifest가 선언한 implementation을 다시 실행해 저장된 report와 JSON 동등성을 비교한다. 학습자 dossier에서는 자신의 `.workspace/13-platform-control-plane/platform_model.py`와 그 report hash를 선언한다.

이 evidence는 idempotency, evidence gate, partial effects, tenant isolation, drift, break-glass, identity fallback 거부, wave abort, cleanup과 deterministic snapshot의 합성 공개 행동만 증명한다.

## Human Review와 한계

Python audit hook은 OS sandbox가 아니다. report는 실제 IAM, network, Kubernetes scheduler/CNI/storage, IaC provider, concurrent reconcile, crash recovery, GitOps controller, telemetry delivery, 비용 또는 physical deletion을 검증하지 않는다. 따라서 `rubric.md`에 따라 실제 owner, SLO denominator/threshold, capacity headroom, policy enforcement, data commitment와 rollback을 사람이 확인해야 한다.

사람 판정은 `EXIT-1..3`마다 충족/보완 필요/범위 밖과 근거를 기록하고, condition에는 owner·due·verification·rollback을 붙인다. 자동 PASS만으로 production readiness 또는 조직적 adoption을 승인하지 않는다.
