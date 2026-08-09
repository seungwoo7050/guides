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

## 외부 controller 없는 결정적 경로

다음 명령은 local Git repository와 JSON desired/live state만 사용합니다. 기존 경로를 덮어쓰지 않습니다.

```sh
test ! -e .workspace/gitops
mkdir -p .workspace/gitops
cp -R examples/optional-labs/gitops/. .workspace/gitops/
git -C .workspace/gitops init
git -C .workspace/gitops add -- desired.json
git -C .workspace/gitops -c user.name=platform-guide -c user.email=platform-guide@example.invalid commit -m 'desired: checkout staging v1'
python3 .workspace/gitops/reconcile.py .workspace/gitops/desired.json .workspace/gitops/live.json
if python3 .workspace/gitops/reconcile.py .workspace/gitops/desired.json .workspace/gitops/live-drift.json; then
  printf '%s\n' 'UNEXPECTED_SUCCESS: live drift was not detected' >&2
  exit 1
else
  reconcile_status=$?
fi
test "$reconcile_status" -eq 1
printf 'EXPECTED_RECONCILE exit=%s\n' "$reconcile_status"
```

검사기는 `service`·`environment` target identity, non-empty revision과 정확한 `sha256:<64 lowercase hex>` digest를 먼저 검증합니다. 다른 target이나 malformed/missing digest는 비교 결과가 아니라 입력 오류이므로 exit `2`로 거부합니다. 첫 검사는 exit `0`과 `action=none`, 두 번째 검사는 exit `1`과 `action=reconcile`이어야 합니다. 같은 digest라도 revision이 다르면 reconcile 대상입니다. 위 `if` block은 expected exit `1`을 명시적으로 확인하므로 fail-fast shell에서도 다음 evidence 단계를 계속 실행할 수 있습니다. 다음으로 live drift를 별도 evidence로 보존하고 desired state를 적용한 결과를 새 파일에 만듭니다.

```sh
cp .workspace/gitops/live-drift.json .workspace/gitops/evidence-live-drift.json
cp .workspace/gitops/desired.json .workspace/gitops/live-reconciled.json
python3 .workspace/gitops/reconcile.py .workspace/gitops/desired.json .workspace/gitops/live-reconciled.json
```

이 경로는 source fetch, render, Kubernetes apply, health assessment, controller credential, suspend와 prune을 실행하지 않습니다. Flux/Argo CD가 없으면 이 profile을 controller 성공으로 표시하지 않습니다.

공통 `check_profiles.py`는 target mismatch, malformed/missing digest와 revision-only drift도 known-bad로 검사합니다. `bounded-break-glass`는 ticket·owner·timezone이 있는 expiry를 요구하고 fixture의 고정 `evaluatedAt`보다 미래이면서 24시간 이내일 때만 허용합니다. 만료됐거나 너무 길거나 해석할 수 없는 예외는 reconcile을 우회하지 못합니다.

## 기본 흐름

1. test repository에 namespace와 작은 workload desired state를 저장합니다.
2. controller가 commit revision을 관찰하고 apply하는지 확인합니다.
3. Git에서 image 또는 replica를 바꾸고 observed revision과 Ready 시간을 기록합니다.
4. cluster에서 live field를 직접 수정해 drift와 correction을 봅니다.
5. controller를 suspend한 뒤 긴급 변경을 적용합니다.
6. 같은 변경을 Git에 반영하거나 되돌리고 controller를 resume합니다.
7. test resource 하나를 Git에서 제거해 prune preview/결과를 확인합니다.
8. controller와 cluster를 cleanup합니다.

실제 controller profile은 [Local Kubernetes 실습](01-kind-kubernetes-lab.md)의 전용 cluster와 별도 local test repository에서만 수행합니다. 설치 전에 공식 문서에서 현재 지원 version과 bootstrap이 만드는 cluster-wide resource를 확인하고 기록합니다. 이 가이드는 production repository에 deploy key를 만들거나 외부 Git host를 변경하는 bootstrap 명령을 자동 실행하지 않습니다.

제품과 무관하게 다음 단계와 evidence는 모두 필요합니다.

```text
source fetch → render → apply/admission → health
desired commit → observed revision → live generation → Ready evidence
suspend ticket/owner/expiry → audited live change → Git 반영 또는 복구 → resume
prune preview → data/finalizer 검토 → prune 결과 → 잔여 inventory
```

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

## Cleanup

실제 controller를 사용했다면 test source, reconciliation object, namespace와 cluster를 controller 공식 제거 순서로 정리하고 cluster-scoped CRD·role·webhook 잔여 여부를 확인합니다. 결정적 경로는 `.workspace/gitops` 밖을 변경하지 않으며 evidence 보존 뒤 학습자가 해당 디렉터리를 명시적으로 삭제합니다.
