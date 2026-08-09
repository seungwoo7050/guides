# Workload unschedulable

## 증상

- Pod 또는 workload가 `Pending`에 머뭅니다.
- Deployment는 desired replica를 가지지만 Available이 증가하지 않습니다.
- Environment provisioning이 workload 단계에서 멈춥니다.

## 먼저 구분할 것

`Pending`이 모두 scheduler 문제는 아닙니다. Image pull, volume attach와 init 작업은 schedule 후에도 지연될 수 있습니다. Pod condition과 event에서 schedule 여부를 먼저 확인합니다.

## 검사 순서

1. Workload의 current generation과 requested replica를 확인합니다.
2. Pod condition과 scheduler event reason을 확인합니다.
3. Resource request, quota와 namespace limit을 비교합니다.
4. Node allocatable, taint/toleration, affinity와 topology를 확인합니다.
5. PVC binding과 storage topology를 확인합니다.
6. Priority/preemption과 다른 tenant의 usage를 확인합니다.
7. Autoscaler가 scale 가능한지, provider quota가 남았는지 확인합니다.
8. 최근 profile default 또는 cluster upgrade를 확인합니다.

## 대표 원인

- CPU/memory/ephemeral storage 부족
- resource quota 초과
- node selector/affinity 불일치
- taint toleration 누락
- topology spread/PDB와 capacity 충돌
- unbound volume
- max node/provider quota
- 잘못된 resource request default
- 특수 hardware 없음

## 안전한 완화

- 잘못된 workload spec이면 application owner가 수정합니다.
- Platform default 결함이면 profile rollout을 중단하고 affected workload를 찾습니다.
- 일시 capacity 부족이면 priority와 production reserve를 보호하면서 scale합니다.
- Preview flood면 low-priority request를 제한하거나 TTL cleanup을 실행합니다.
- 특정 zone 장애면 topology와 storage 제약을 확인한 뒤 다른 zone을 사용합니다.

Request를 무조건 낮추거나 constraint를 제거하지 않습니다. OOM, 성능 저하와 isolation 위반을 뒤로 미룰 수 있습니다.

## 복구 판정

- Pod가 schedule되고 workload Ready가 됩니다.
- Platform condition이 current generation에서 갱신됩니다.
- 다른 tenant의 SLO와 capacity reserve가 유지됩니다.
- 임시 quota/priority/constraint 변경이 정리됩니다.
- Capacity forecast와 profile default가 수정됩니다.
