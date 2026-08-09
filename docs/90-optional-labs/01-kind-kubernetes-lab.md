# Local Kubernetes 실습

폐기 가능한 local cluster에서 Kubernetes API와 controller가 desired state를 유지하는 과정을 관찰합니다. `kind`를 예로 들지만 동등한 로컬 환경을 사용할 수 있습니다.

## 목표

- API object의 spec·status·metadata를 구분합니다.
- Deployment controller가 Pod를 재생성하는 과정을 봅니다.
- Service와 label selector의 연결을 확인합니다.
- resource request, scheduling failure와 event를 관찰합니다.
- namespace 삭제와 cluster cleanup의 범위를 확인합니다.

## 사전 조건

- Docker Engine 또는 동등한 container runtime
- `kubectl`
- `kind` 또는 동등 local cluster
- 외부 production kubeconfig와 분리된 context

작업 전에 현재 context를 확인합니다.

```sh
kubectl config current-context
kubectl config get-contexts
```

실습용 이름을 명시하고 기존 context를 덮어쓰지 않습니다.

## 기본 흐름

1. local cluster를 생성합니다.
2. 전용 namespace를 만듭니다.
3. [`examples/kubernetes/workload-contract.yaml`](../../examples/kubernetes/workload-contract.yaml)을 복사해 image와 필요한 값을 안전한 local 예제로 조정합니다.
4. object의 generation, observedGeneration과 condition을 조회합니다.
5. Pod 하나를 직접 삭제하고 controller가 desired replica를 복원하는지 봅니다.
6. Service selector를 잘못 바꿔 endpoint가 사라지는 실패를 주입합니다.
7. resource request를 cluster capacity보다 크게 설정해 `Pending`과 scheduling event를 관찰합니다.
8. 변경을 되돌리고 Ready와 endpoint를 확인합니다.
9. namespace와 cluster를 삭제합니다.

## 관측 명령 예

```sh
kubectl get deploy,pod,svc -n platform-lab -o wide
kubectl get deployment demo -n platform-lab -o yaml
kubectl get events -n platform-lab --sort-by=.metadata.creationTimestamp
kubectl describe pod -n platform-lab POD_NAME
kubectl get endpointslice -n platform-lab
```

명령 출력 전체를 무작정 저장하지 말고 다음 필드를 기록합니다.

- `metadata.generation`
- `status.observedGeneration`
- `status.conditions`
- Pod owner reference
- scheduler reason
- Service/EndpointSlice label 관계

## 실패 질문

- Deployment가 존재하지만 Ready replica가 0일 때 platform API는 어떤 condition을 보여야 합니까?
- Service object가 있어도 endpoint가 없는 상태를 완료로 볼 수 있습니까?
- Scheduling 실패는 application team, platform team 또는 capacity owner 중 누구의 책임입니까?
- 사용자가 retry해야 합니까, spec을 바꿔야 합니까, platform capacity를 늘려야 합니까?

## Cleanup

```sh
kubectl delete namespace platform-lab --wait=true
kind delete cluster --name platform-guide
```

최종적으로 cluster/container가 남지 않았는지 확인합니다. 강제 삭제를 사용했다면 finalizer와 외부 resource가 남지 않았는지도 기록합니다.
