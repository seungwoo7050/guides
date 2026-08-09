# Admission policy 실습

Local cluster에서 policy를 audit/warn/deny 단계로 적용하고, 정상 workload와 위반 workload의 결과를 비교합니다. Kubernetes CEL, Kyverno 또는 Gatekeeper 중 하나를 선택합니다.

## 목표

- policy를 source 검사와 runtime admission에서 각각 적용하는 이유를 봅니다.
- audit/warn/deny rollout의 차이를 확인합니다.
- error message와 remediation이 사용자에게 전달되는지 확인합니다.
- policy exception의 scope와 expiry를 설계합니다.
- policy 또는 webhook 장애 때 fail-open/fail-closed 결과를 검토합니다.

## 예시 정책

- privileged container 금지
- hostPath 또는 host namespace 제한
- image tag 대신 digest 요구
- resource request 필수
- owner/profile label 필수

모든 정책을 한 번에 강제하지 않습니다. 하나를 선택해 lifecycle을 완성합니다.

## 외부 controller 없는 결정적 경로

```sh
python3 examples/optional-labs/check_profiles.py
```

`policy/production-digest-allowed`, `policy/production-tag-denied`, `policy/production-malformed-digest-denied`, `policy/production-init-tag-denied`, `policy/staging-tag-out-of-scope`가 선언한 allow/deny와 일치해야 합니다. 이 검사는 JSON request에 대한 작은 판정이며 Kubernetes admission, CEL type checking, webhook timeout이나 기존 workload migration을 증명하지 않습니다.

## Kubernetes CEL profile

[Local Kubernetes 실습](01-kind-kubernetes-lab.md)의 `kind-platform-guide` context와 `platform-lab` namespace만 사용합니다. 먼저 context, namespace, API 지원과 고정 실습 이름의 충돌 여부를 확인합니다. 첫 다섯 명령 중 하나라도 실패하면 기존 객체를 덮어쓰지 말고 이 profile을 `SKIP`으로 남깁니다.

```sh
test "$(kubectl config current-context)" = kind-platform-guide
kubectl --context kind-platform-guide get namespace platform-lab
kubectl --context kind-platform-guide api-resources --api-group=admissionregistration.k8s.io | grep ValidatingAdmissionPolicy
test -z "$(kubectl --context kind-platform-guide get validatingadmissionpolicy platform-guide-image-digest --ignore-not-found -o name)"
test -z "$(kubectl --context kind-platform-guide get validatingadmissionpolicybinding platform-guide-image-digest --ignore-not-found -o name)"
kubectl --context kind-platform-guide apply -f examples/optional-labs/policy/admission-policy.yaml
kubectl --context kind-platform-guide apply --dry-run=server -f examples/optional-labs/policy/allowed-deployment.yaml
expect_denied() {
  fixture=$1
  if kubectl --context kind-platform-guide apply --dry-run=server -f "$fixture"; then
    printf 'UNEXPECTED_SUCCESS: %s was admitted\n' "$fixture" >&2
    return 1
  else
    denied_status=$?
  fi
  test "$denied_status" -eq 1 || return 1
  printf 'EXPECTED_DENIAL fixture=%s exit=%s\n' "$fixture" "$denied_status"
}
expect_denied examples/optional-labs/policy/denied-deployment.yaml
expect_denied examples/optional-labs/policy/malformed-digest-deployment.yaml
expect_denied examples/optional-labs/policy/init-tag-denied-deployment.yaml
```

정상 fixture는 server dry-run에 통과하고 app container tag, malformed digest 및 init container tag fixture는 `platform-lab workload image에는 immutable sha256 digest가 필요합니다.` 메시지로 거부돼야 합니다. `--dry-run=server`이므로 workload와 image pull은 생성하지 않습니다. `expect_denied`는 각 expected denial의 exit `1`을 확인하므로 fail-fast shell에서도 모든 fixture의 stderr와 status를 evidence로 기록합니다.

정책을 `Deny`로 적용하기 전 실제 조직에서는 `Audit`/`Warn` inventory, 대표 workload, owner, remediation, exception과 migration deadline이 필요합니다. 이 local fixture는 새 요청 세 개만 비교합니다.

## 기본 흐름

1. 위반 workload와 정상 workload fixture를 작성합니다.
2. audit 또는 warn mode에서 inventory를 수집합니다.
3. policy ID, owner, message와 remediation을 보완합니다.
4. test namespace에서 deny mode를 적용합니다.
5. 정상 workload 통과와 위반 workload 거부를 확인합니다.
6. 좁은 scope와 expiry를 가진 exception을 설계하거나 적용합니다.
7. policy controller 장애 또는 timeout을 안전하게 모의해 failure policy를 확인합니다.
8. policy와 test resource를 cleanup합니다.

## 검토 질문

- 사용자가 배포 마지막 단계 전에 같은 오류를 확인할 수 있습니까?
- Deny message가 어떤 field를 어떻게 수정할지 알려 줍니까?
- Existing workload에는 어떤 migration과 deadline을 제공합니까?
- Exception이 전체 namespace 또는 cluster에 과도하게 적용되지 않습니까?
- Policy controller 장애가 모든 deployment를 막아야 합니까?
- Policy change 자체가 version·review·canary·rollback을 가집니까?

## Cleanup

```sh
test "$(kubectl config current-context)" = kind-platform-guide
kubectl --context kind-platform-guide delete -f examples/optional-labs/policy/admission-policy.yaml --ignore-not-found=true
kubectl --context kind-platform-guide get validatingadmissionpolicies,validatingadmissionpolicybindings
```

정책과 dry-run 외의 test resource가 남지 않았는지 확인합니다. 실제 webhook/controller profile을 사용했다면 deployment, service, CRD, cluster role과 webhook configuration을 별도로 inventory하고 제거합니다.
