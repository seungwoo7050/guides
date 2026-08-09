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

```sh
docker version
kubectl version --client
kind version
```

이 profile은 `python:3.12.11-alpine3.22` base image를 최초 build할 때 network를 사용할 수 있습니다. 아래 검사는 최종 local image ID를 기록하지만 mutable base tag의 registry digest까지 증명하지는 않습니다. 실제 실행에서는 build log의 resolved base digest도 evidence에 남기거나 검토한 digest로 `FROM`을 고정합니다. `kind`가 없거나 image pull이 허용되지 않으면 [결정적 대체 검사](00-index.md#외부-도구가-없는-필수-대체-경로)를 수행하고 이 profile은 `SKIP`으로 남깁니다.

작업 전에 현재 context를 확인합니다.

```sh
kubectl config current-context
kubectl config get-contexts
```

실습용 이름을 명시하고 기존 context를 덮어쓰지 않습니다.

## 준비와 정상 경로

기존 workspace, cluster와 image tag를 덮어쓰지 않습니다. 아래 세 `test` 중 하나라도 실패하면 이름을 바꾸거나 기존 자원의 owner를 확인하기 전에는 계속하지 않습니다.

```sh
test ! -e .workspace/kind-platform
test -z "$(kind get clusters | awk '$0 == "platform-guide" {print}')"
test -z "$(docker image ls --quiet platform-guide/http-echo:v1)"
mkdir -p .workspace/kind-platform
cp -R examples/optional-labs/kind/. .workspace/kind-platform/
docker build -t platform-guide/http-echo:v1 .workspace/kind-platform
docker image inspect platform-guide/http-echo:v1 --format 'local-image-id={{.Id}}'
kind create cluster --name platform-guide --config .workspace/kind-platform/kind-config.yaml
kind load docker-image platform-guide/http-echo:v1 --name platform-guide
test "$(kubectl config current-context)" = kind-platform-guide
kubectl --context kind-platform-guide apply -f .workspace/kind-platform/workload.yaml
kubectl --context kind-platform-guide wait --for=condition=Available deployment/checkout -n platform-lab --timeout=120s
kubectl --context kind-platform-guide get deploy,pod,svc,endpointslice -n platform-lab -o wide
```

`kubectl config current-context`가 `kind-platform-guide`가 아니면 다음 명령을 실행하지 않습니다. 별도 terminal에서 local port-forward를 열고 `curl http://127.0.0.1:18080/ready`가 `ok`를 반환하는지 확인한 뒤 port-forward를 종료합니다.

```sh
test "$(kubectl config current-context)" = kind-platform-guide
kubectl --context kind-platform-guide port-forward -n platform-lab service/checkout 18080:80
```

Pod 하나를 지우고 새 UID로 두 replica가 다시 Ready가 되는지 관찰합니다.

```sh
test "$(kubectl config current-context)" = kind-platform-guide
POD_NAME="$(kubectl --context kind-platform-guide get pod -n platform-lab -l app=checkout --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')"
test -n "$POD_NAME"
OLD_UID="$(kubectl --context kind-platform-guide get pod "$POD_NAME" -n platform-lab -o jsonpath='{.metadata.uid}')"
kubectl --context kind-platform-guide delete pod "$POD_NAME" -n platform-lab --wait=true
attempt=0
POD_COUNT=0
while [ "$attempt" -lt 60 ]; do
  POD_COUNT="$(kubectl --context kind-platform-guide get pod -n platform-lab -l app=checkout -o name | awk 'END {print NR}')"
  [ "$POD_COUNT" = 2 ] && break
  attempt=$((attempt + 1))
  sleep 2
done
test "$POD_COUNT" = 2
kubectl --context kind-platform-guide wait --for=condition=Ready pod -l app=checkout -n platform-lab --timeout=120s
test "$(kubectl --context kind-platform-guide get deployment checkout -n platform-lab -o jsonpath='{.status.readyReplicas}')" = 2
kubectl --context kind-platform-guide get pod -n platform-lab -l app=checkout -o custom-columns=NAME:.metadata.name,UID:.metadata.uid
test -z "$(kubectl --context kind-platform-guide get pod -n platform-lab -l app=checkout -o jsonpath='{range .items[*]}{.metadata.uid}{"\n"}{end}' | awk -v old="$OLD_UID" '$0 == old {print}')"
```

## 실패 주입과 복구

Service selector drift를 주입하면 Service object는 남지만 EndpointSlice endpoint가 사라져야 합니다.

```sh
test "$(kubectl config current-context)" = kind-platform-guide
kubectl --context kind-platform-guide patch service checkout -n platform-lab --type=merge -p '{"spec":{"selector":{"app":"missing"}}}'
kubectl --context kind-platform-guide get service,endpointslice -n platform-lab -o yaml
kubectl --context kind-platform-guide patch service checkout -n platform-lab --type=merge -p '{"spec":{"selector":{"app":"checkout"}}}'
kubectl --context kind-platform-guide get endpointslice -n platform-lab
```

불가능한 CPU request를 새 revision에 적용해 `Pending`과 scheduler event를 관찰한 뒤 이전 revision으로 복구합니다.

```sh
test "$(kubectl config current-context)" = kind-platform-guide
kubectl --context kind-platform-guide patch deployment checkout -n platform-lab --type=strategic -p '{"spec":{"template":{"spec":{"containers":[{"name":"app","resources":{"requests":{"cpu":"1000","memory":"32Mi"},"limits":{"cpu":"1000","memory":"64Mi"}}}]}}}}'
kubectl --context kind-platform-guide get pod -n platform-lab -o wide
kubectl --context kind-platform-guide get events -n platform-lab --sort-by=.metadata.creationTimestamp
kubectl --context kind-platform-guide rollout undo deployment/checkout -n platform-lab
kubectl --context kind-platform-guide rollout status deployment/checkout -n platform-lab --timeout=120s
```

## 관측 명령 예

```sh
kubectl --context kind-platform-guide get deploy,pod,svc -n platform-lab -o wide
kubectl --context kind-platform-guide get deployment checkout -n platform-lab -o yaml
kubectl --context kind-platform-guide get events -n platform-lab --sort-by=.metadata.creationTimestamp
kubectl --context kind-platform-guide describe pod -n platform-lab POD_NAME
kubectl --context kind-platform-guide get endpointslice -n platform-lab
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
test "$(kubectl config current-context)" = kind-platform-guide
kubectl --context kind-platform-guide delete namespace platform-lab --wait=true
kind delete cluster --name platform-guide
docker image rm platform-guide/http-echo:v1
test -z "$(kind get clusters | awk '$0 == "platform-guide" {print}')"
```

최종적으로 cluster/container/network와 `.workspace/kind-platform` 외의 상태가 남지 않았는지 확인합니다. workspace는 evidence를 보존한 뒤 학습자가 명시적으로 정리합니다. 강제 삭제를 사용했다면 finalizer와 외부 resource가 남지 않았는지도 기록합니다.
